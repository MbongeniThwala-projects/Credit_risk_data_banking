'''synthetic SA loan book generator, V1

products: home loans, asset finance, personal loans
'''
import numpy as np
import pandas as pd
import argparse
from pathlib import Path

from generator.reference import(BUREAU_BAND_EDGES, BUREAU_BAND_LABELS, MACRO_STRESS, PRODUCTS, PROVINCE_WEIGHTS, load_prime_path)

#Behaviour params
B_SCORE = -1.2                          # better score lowers the chances of missing a payment
B_DIT = .5                              # higher instalment to income eaises it
B_SHOCK = .25                           # each percentage point of prime increase since origination raise it
CURE_BASE = {1: .55, 2: .35, 3: .20}    #chance of catching up, by months missed
PREPAY_PROB = .003
WRITE_OFF_DPD = 360                     # balance is written off after about 12 months past due date

def annuity(balance, monthly_rate, n_months):
    '''level monthly instalment that repays the balance over n_months'''
    return balance * monthly_rate / (1.0 - (1.0 + monthly_rate) ** (-n_months))

def bucket(dpd):
    return np.select(
        [dpd == 0, dpd < 30, dpd < 60, dpd < 90],
        ["current", "1-29", "30-59", "60-89"],
        default="90+"
    )

def build_borrowers_and_loans(n, rng, prime):
    product_name = list(PRODUCTS)
    product = rng.choice(product_name, size=n, p=[PRODUCTS[p]["share"] for p in product_name])

    province = rng.choice(list(PROVINCE_WEIGHTS), size=n, p=list(PROVINCE_WEIGHTS.values()))
    income = np.clip(rng.lognormal(np.log(22_000), .6, n), 6_000, 250_000).round(-2)
    score = np.clip(rng.normal(640, 85, n), 300, 950).round().astype(int)
    band = np.array(BUREAU_BAND_LABELS)[np.digitize(score, BUREAU_BAND_EDGES)]

    n_months = len(prime)
    orig_idx = rng.integers(0, n_months -3, n) #lets at least have 3 snapshots per loan
    prime_orig = prime["prime_rate"].to_numpy()[orig_idx]

    margin = np.zeros(n)
    term = np.zeros(n, dtype=int)
    principal = np.zeros(n)
    ltv = np.full(n, np.nan)
    for name, cfg in PRODUCTS.items():
        idx = np.where(product == name)[0]
        k = len(idx)
        lo, hi = cfg["margin_range"]
        risk = np.clip((750 - score[idx]) / 450, 0, 1)
        margin[idx] = rng.choice(cfg["terms"], size=k, p=cfg["term_probs"])

        r = (prime_orig[idx] + margin[idx]) / 100 / 12
        target_instalment = rng.uniform(*cfg["dti_range"], k) * income[idx]
        pv = target_instalment * (1 - (1 + r) ** (-term[idx])) / r
        principal[idx] = np.clip(pv, *cfg["principal_range"]).round(-2)
        if cfg["ltv_range"] is not None:
            ltv[idx] = rng.uniform(*cfg["ltv_range"], k)

    r0 = (prime_orig + margin) / 100 / 12
    first_instalment = annuity(principal, r0, term)

    ids = np.arange(1, n + 1)
    borrowers = pd.DataFrame(
        {
            "borrower_id": [f"B{i:07d}" for i in ids],
            "province": province,
            "monthly_income_zar": income,
            "bureau_score": score,
            "bureau_band": band
        }
    )
    loans = pd.DataFrame(
        {
            "loan_id": [f"L{i:07d}" for i in ids],
            "borrower_id": borrowers["borrower_id"],
            "product": product,
            "origination_month": prime.index[orig_idx].to_timestamp(how="end").normalize(),
            "principal_zar": principal,
            "term_months": term,
            "margin_over_prime": margin.round(2),
            "prime_at_origination": prime_orig,
            "instalment_to_income": (first_instalment / income).round(4),
            "ltv_at_origination": ltv.round(3),
            "collateral_value_zar": np.where(np.isnan(ltv), np.nan, (principal/ltv).round(-2))
        }
    )
    return borrowers, loans, orig_idx, prime_orig, margin

def simulate(loans, borrowers, orig_idx, prime_orig, margin, prime, rng):
    n = len(loans)
    n_months = len(prime)
    month_end = prime.index.to_timestamp(how="end").normalize()
    prime_path = prime["prime_rate"].to_numpy()

    product = loans["product"].to_numpy()
    base_logit = np.array([PRODUCTS[p]["base_logit"] for p in product])
    z_score = (borrowers["bureau_score"].to_numpy() - 650) / 100
    z_dti = (loans["instalment_to_income"].to_numpy() - .18) / .08
    macro = np.array([MACRO_STRESS.get(str(m), 0.0) for m in prime.index])

    balance = loans["principal_zar"].to_numpy().astype(float)
    n_rem = loans["term_months"].to_numpy().astype(int)
    arrears = np.zeros(n)
    months_missed = np.zeros(n, dtype=int)
    first_dpd = np.zeros(n, dtype=int)
    defaulted = np.zeros(n, dtype=bool)
    closed = np.zeros(n, dtype=bool)
    first_default_idx = np.full(n, -1)

    frames = []
    for t in range(n_months):
        live = (orig_idx <= t) & ~closed
        if not live.any():
            continue
        i = np.where(live)[0]

        rate = (prime_path[t] + margin[i]) / 100 / 12
        opening = balance[i]
        interest = opening * rate
        n_eff = np.maximum(n_rem[i], 1)
        instalment = annuity(opening, rate, n_eff)

        m = months_missed[i]
        logit = (
            base_logit[i]
            + B_SCORE * z_score[i]
            + B_DIT * z_dti[i]
            + B_SHOCK * (prime_path[t] - prime_orig[i])
            + macro[t]
        )
        p_miss = 1 / (1 + np.exp(-logit))
        cure_p = np.clip(np.array([CURE_BASE.get(int(k), 0.0) for k in m]) + .08 * z_score[i], .02, .95)
        draw = rng.random(len(i))
        was_def = defaulted[i]
        miss = np.where(m==0, draw < p_miss, draw >= cure_p)
        miss = miss | was_def       #defaulted accounts stay unpaid

        prepay = (~miss) & (m == 0) & (rng.random(len(i)) < PREPAY_PROB)
        paid = np.where(miss, 0.0, instalment + arrears[i])
        paid = np.where(prepay, opening + interest, paid)
        paid = np.minimum(paid, opening + interest)     #never pay more than is owed
        closing = opening + interest - paid

        new_arrears = np.where(miss, arrears[i] + instalment, 0.0)
        new_m = np.where(miss, m + 1, 0)
        d0 = np.where(miss & (m == 0), rng.integers(1, 31, len(i)), first_dpd[i])
        dpd = np.where(new_m > 0, d0 + 30 * (new_m -1), 0)
        now_def = was_def | (dpd >= 90)
        paid_off = (~miss) & (closing < 1.0)
        write_off = miss & (dpd >= WRITE_OFF_DPD)
        written_off_amount = np.where(write_off, closing, 0.0)
        closing = np.where(paid_off | write_off, 0.0, closing)
        newly_closed = paid_off | write_off

        #Track the first month each loan reaches 90+ days past due
        hit = now_def & ~was_def
        first_default_idx[i[hit]] = t

        status = np.select(
            [write_off, paid_off, now_def, dpd > 0],
            ["written_off", "closed", "default", "arrears"],
            default="current"
        )
        frames.append(
            pd.DataFrame(
                {
                    "loan_id": loans["loan_id"].to_numpy()[i],
                    "snapshot_date": month_end[t],
                    "opening_balance": opening.round(2),
                    "interest_charged": interest.round(2),
                    "instalment_due": instalment.round(2),
                    "amount_paid": paid.round(2),
                    "wriitten_off_amount": written_off_amount.round(2),
                    "closing_balance": closing.round(2),
                    "arrears_amount": new_arrears.round(2),
                    "days_past_due": dpd,
                    "delinquency_bucket": bucket(dpd),
                    "status": status,
                    "prime_rate": prime_path[t]
                }
            )
        )

        balance[i] = closing
        arrears[i] = new_arrears
        months_missed[i] = new_m
        first_dpd[i] = d0
        defaulted[i] = now_def
        closing[i] = newly_closed
        n_rem[i] = np.maximum(n_rem[i] - 1, 0)

    snapshots = pd.concat(frames, ignore_index=True)
    first_default_month = pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    has = first_default_idx >= 0
    first_default_month[has] = month_end[first_default_idx[has]]
    return snapshots, first_default_month.to_numpy()


def main():
    parser = argparse.ArgumentParser(description="Generate a synthetic South African loan book")
    parser.add_argument("--n-loans", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    prime = load_prime_path()

    borrowers, loans, orig_idx, prime_orig, margin = build_borrowers_and_loans(
        args.n_loans, rng, prime
    )
    snapshots, first_default_month = simulate(
        loans, borrowers, orig_idx, prime_orig, margin, prime, rng
    )
    loans["first_default_month"] = first_default_month

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    borrowers.to_parquet(out / "borrowers.parquet", index=False)
    loans.to_parquet(out / "loans.parquet", index=False)
    snapshots.to_parquet(out / "loan_monthly_snapshots.parquet", index=False)

    last = snapshots["snapshot_date"].max()
    print(f"loans: {len(loans):,}   loan-month rows: {len(snapshots):,}")
    print("\nShare of loans that reached 90+ days past due, by product:")
    rate = loans.groupby("product")["first_default_month"].apply(lambda s: s.notna().mean())
    print((rate * 100).round(1).astype(str) + " %")
    print(f"\nDelinquency buckets in the last month ({last.date()}):")
    print(snapshots.loc[snapshots["snapshot_date"] == last, "delinquency_bucket"].value_counts())
    print("\nFiles written to", out.resolve())


if __name__ == "__main__":
    main()