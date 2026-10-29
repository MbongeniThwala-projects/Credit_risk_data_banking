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
    check("one snapshot per loan per month", not snaps.duplicated)