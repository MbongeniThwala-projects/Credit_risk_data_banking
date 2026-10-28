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