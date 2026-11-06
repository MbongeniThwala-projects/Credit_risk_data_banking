"""Write the loan book as lake-style extracts, ready to upload to Cloud Storage.

Run from the project root:  python -m generator.export_extracts
The extracts are only written if the plausibility gate passes (use --force to override).
"""
import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd


def plausibility_problems(borrowers, loans, snaps):
    """Return reasons the data looks wrong. An empty list means it passed."""
    problems = []
    n_loans = len(loans)

    rows_per_loan = len(snaps) / n_loans
    if not 10 <= rows_per_loan <= 30:
        problems.append(
            f"average snapshots per loan is {rows_per_loan:.1f}, expected between 10 and 30"
        )

    last = snaps[snaps["snapshot_date"] == snaps["snapshot_date"].max()]
    live_share = len(last) / n_loans
    if live_share < 0.7:
        problems.append(f"only {live_share:.0%} of loans are live in the last month, expected 70% or more")

    in_default = (last["delinquency_bucket"] == "90+").mean()
    if in_default > 0.10:
        problems.append(
            f"{in_default:.0%} of live loans are 90+ days past due in the last month, expected under 10%"
        )

    by_product = loans.groupby("product")["first_default_month"].apply(lambda s: s.notna().mean())
    for product, rate in by_product.items():
        if not 0.005 <= rate <= 0.20:
            problems.append(f"{product} default share is {rate:.1%}, expected between 0.5% and 20%")

    joined = loans.merge(borrowers, on="borrower_id")
    defaulted = joined["first_default_month"].notna()
    weak = joined["bureau_band"].isin(["Poor", "Unfavourable"])
    strong = joined["bureau_band"].isin(["Good", "Excellent"])
    if weak.any() and strong.any() and defaulted[weak].mean() < 2 * defaulted[strong].mean():
        problems.append("weak bureau bands should default at least twice as often as strong ones")

    return problems


def write_extracts(borrowers, loans, snaps, out):

    loans = loans.assign(first_default_month=loans["first_default_month"].astype("datetime64[us]"))

    for name in ["loan_snapshots", "loans", "borrowers"]:
        shutil.rmtree(out / name, ignore_errors=True)

    snaps = snaps.copy()
    snaps["snapshot_month"] = snaps["snapshot_date"].dt.strftime("%Y-%m")
    for month, part in snaps.groupby("snapshot_month"):
        folder = out / "loan_snapshots" / f"snapshot_month={month}"
        folder.mkdir(parents=True, exist_ok=True)
        part.drop(columns="snapshot_month").to_parquet(folder / "part-0000.parquet", index=False)

    for name, frame in {"loans": loans, "borrowers": borrowers}.items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(folder / f"{name}.parquet", index=False)


def main():
    parser = argparse.ArgumentParser(description="Export lake-style extracts")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="data/lake")
    parser.add_argument("--force", action="store_true", help="export even if the gate fails")
    args = parser.parse_args()

    data = Path(args.data)
    borrowers = pd.read_parquet(data / "borrowers.parquet")
    loans = pd.read_parquet(data / "loans.parquet")
    snaps = pd.read_parquet(data / "loan_monthly_snapshots.parquet")

    problems = plausibility_problems(borrowers, loans, snaps)
    if problems and not args.force:
        print("The data does not look right, so nothing was exported:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    out = Path(args.out)
    write_extracts(borrowers, loans, snaps, out)
    files = [f for f in out.rglob("*.parquet")]
    size_mb = sum(f.stat().st_size for f in files) / 1e6
    print(f"Gate passed. Wrote {len(files)} files ({size_mb:.1f} MB) to {out.resolve()}")


if __name__ == "__main__":
    main()