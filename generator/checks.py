'''checking our loan book
'''

import argparse
import sys
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Check the generated loan book")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    data = Path(args.data)

    borrowers = pd.read_parquet(data / "borrowers.parquet")
    loans = pd.read_parquet(data / "loans.parquet")
    snaps = pd.read_parquet(data / "loan_monthly_snapshots.parquet")

    results = []

    def check(name, passed):
        results.append(passed)
        print(f"{'PASS' if passed else 'FAIL'} {name}")

    check("loan_id is unique", loans["loan_id"].is_unique)
    check("every loan had a borrower", loans["borrower_id"].isin(borrowers["borrower_id"]).all())
    check("one snapshot per loan per month", not snaps.duplicated(["loan_id", "snapshot_date"]).any())

    flow_error = (
        snaps["opening_balance"]
        + snaps["interest_charged"]
        - snaps["amount_paid"]
        - snaps["written_off_amount"]
        - snaps["closing_balance"]
    ).abs()
    check("balance roll forward ties out (within R1)", flow_error.max() < 1.0)
    check("no negative balance", (snaps["closing_balance"] >= 0).all())
    check("days past due is never negative", (snaps["days_past_due"] >= 0).all())

    written_off = snaps.loc[snaps["status"] == "written_off", ["loan_id", "snapshot_date"]]
    written_off = written_off.rename(columns={"snapshot_date": "written_off_date"})
    after = snaps.merge(written_off, on="loan_id")
    check("no snapshots after a write off", not (after["snapshot_date"] > after["written_off_date"]).any())

    joined = loans.merge(borrowers, on="borrower_id")
    default_rate = joined.groupby("bureau_band")["first_default_month"].apply(lambda s: s.notna().mean())
    print("\nShare of loans that reached 90+ days past due, by bureau band:")
    print((default_rate * 100).round(1).sort_values(ascending=False).astype(str) + " %")

    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()