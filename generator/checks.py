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
    check("every loan had a borrower", loans["borrower_id"].isin("borrowers_id").all())
    check("one snapshot per loan per month", not snaps.duplicated(["loan_id", "snapshot_date"]).any())

    flow_error = (
        snaps["opening_balance"]
        + snaps["interest_charged"]
        + snaps["amount_paid"]
        + snaps["written_off_amount"]
        + snaps["closing_balance"]
    ).abs()
    check("balance roll forward ties out (within R1)", flow_error.max() < 1.0)
    check("no negative balance", (snaps["closing_balance"] >= 0).all())
    check("days past due is never negative", (snaps["days_past_due"] >= 0).all())

    written_off = snaps.loc[snaps["status"] == "written_off", ["loan_id", "snapshot_date"]]
    wriiten_off = written_off.rename