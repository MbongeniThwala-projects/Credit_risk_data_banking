"""Print the settings and data the generator is really using, to find what is wrong.

Run from the project root:  python -m generator.diagnose
"""
import pandas as pd

from generator import generate, reference

print("=== RATE FILE (expected 9 rows, 2023-05 at 8.25 up to 2026-09 at 7.25) ===")
print(reference.REPO_RATE_FILE.read_text())

prime = reference.load_prime_path()
print("=== PRIME PATH (expected 33 rows: 11.75 in 2024-01, 10.75 in 2026-09) ===")
print(prime.to_string())

print("\n=== PRODUCTS ===")
for name, cfg in reference.PRODUCTS.items():
    keys = ["share", "margin_range", "dti_range", "principal_range", "base_logit"]
    print(name, {k: cfg[k] for k in keys})

print("\n=== BEHAVIOUR (expected -1.2, 0.5, 0.25, 0.003, 360) ===")
# print(generate.B_SCORE, generate.B_DTI, generate.B_SHOCK, generate.PREPAY_PROB, generate.WRITE_OFF_DPD)
# print("CURE_BASE", generate.CURE_BASE)
for name in dir(generate):
    if name.startswith(("B_", "CURE", "PREPAY", "WRITE")):
        print(name, "=", getattr(generate, name))
print("MACRO_STRESS", reference.MACRO_STRESS)
print("PRIME_SPREAD", reference.PRIME_SPREAD, "| window", reference.WINDOW_START, "to", reference.WINDOW_END)

print("\n=== GENERATED LOANS ===")
loans = pd.read_parquet("data/loans.parquet")
cols = ["principal_zar", "margin_over_prime", "prime_at_origination", "instalment_to_income"]
print(loans[cols].describe().round(2).to_string())

snaps = pd.read_parquet("data/loan_monthly_snapshots.parquet")
print("\nMissing interest values in snapshots:", int(snaps["interest_charged"].isna().sum()))
print("Prime values seen in snapshots:", sorted(snaps["prime_rate"].unique())[:12])