'''Reference data and parameters for the synthetic SA loan book

Everything in here is "fake" and for illustrative purposes. It is shaped to give a realistic spread of 
outcomes and is not calibrated to any portfolio.
'''

from pathlib import Path

import numpy as np
import pandas as pd

REPO_RATE_FILE = Path(__file__).resolve().parent.parent / "reference" / "SARB_repo_rate.csv"

#SA prime landing rate = repo + 3.5 % points
PRIME_SPREAD = 3.5

# monthly snapshot window
WINDOW_START = "2024-01"
WINDOW_END = "2026-09"

#Illustrative weights, skewed towards the urban and banking provinces
PROVINCE_WEIGHTS = {
    "Gauteng": .34,
    "KwaZulu": .16,
    "Western Cape": .17,
    "Eastern Cape": .08,
    "Mpumalanga": .07,
    "Limpopo": .05,
    "North West": .05,
    "Free State": .05,
    "Northern Cape": .03,
}

# credit score
BUREAU_BAND_EDGES = [487, 527, 583, 614, 681, 767]
BUREAU_BAND_LABELS = [
    "Poor",
    "Unfavourable",
    "Below average",
    "Average",
    "favourable",
    "Good",
    "Excellent"
]

#Margin over prime is a range: the best credit scores get the low end
PRODUCTS = {
    "home_loan": {
        "share": .20,
        "terms": [240, 300],
        "term_probs": [.5, .5],
        "margin_range": (-1.0, 1.5),
        "dti_range": (.18, .32),
        "principal_range": (300_000, 600_000),
        "ltv_range": (.70, 1.00),
        "base_logit": -6.1
    },
    "vehicle_asset_finance": {
        "share": .30,
        "terms": [48, 60, 72, 84],
        "term_probs": [.1, .3, .4, .2],
        "margin_range": (.0, 4.0),
        "dti_range": (.10, .22),
        "principal_range": (80_000, 1_500_000),
        "ltv_range": (.85, 1.10),
        "base_logit": -5.1
    },
    "home_loan": {
        "share": .50,
        "terms": [12, 24, 36, 48, 60, 72],
        "term_probs": [.05, .15, .25, .20, .20, .15],
        "margin_range": (3.0, 12.0),
        "dti_range": (.05, .18),
        "principal_range": (5_000, 300_000),
        "ltv_range": None,
        "base_logit": -4.1
    },
}

#Scenario assumptions -> extramonthly stress during the 2026 fuel price shock and rate hikes
MACRO_STRESS = {
    "2026-05": .10,
    "2026-06": .20,
    "2026-07": .30,
    "2026-08": .30,
    "2026-09": .30
}

def load_prime_path():
    '''monthly repo and prime rate path for the snapshot window.'''
    months = pd.period_range(WINDOW_START, WINDOW_END, freq="M")
    changes = pd.read_csv(REPO_RATE_FILE)
    changes["month"] = pd.PeriodIndex(changes["effective_month"], freq="M")
    changes = changes.set_index("month")["repo_rate"].sort_index()

    repo = changes.reindex(changes.index.union(months)).ffill().reindex(months)
    path = pd.DataFrame({"repo_rate": repo})
    path["prime_rate"] = path["repo_rate"] + PRIME_SPREAD
    return path