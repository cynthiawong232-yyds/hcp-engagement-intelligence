"""The holdout experiment: designed and priced, deliberately not run.

Every other file in this project tries to recover a causal effect from data
where SALES REPS chose who to visit. hei.trends showed that choice is tied to
the outcome, and hei.uplift showed the per-doctor ranking that results is no
better than random.

A holdout removes the problem at the source. Instead of repairing a biased
comparison afterwards, you take a RANDOM group of doctors and deliberately send
no reps to them. Random assignment makes the groups comparable on everything,
including the variables nobody measured or thought of. No parallel trends
assumption. No worry about whether enough was controlled for.

WE DO NOT RUN THIS. We have no sales force. What we produce is the design:
how many doctors it needs, what it costs, how long it takes, and which
questions are too small to answer at any price worth paying.

That last part is the real deliverable. Telling an executive "the effect you
want measured cannot be detected for less than X" BEFORE the money is spent is
worth more than any model in this repository.

Run it:
    python -m hei.experiment
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from hei import config

OUTCOME = "rx_total"

# Standard two-sample power calculation, 80% power and 5% significance,
# two-sided:
#
#     n per arm  =  2 * (z[a/2] + z[b])^2 * sigma^2 / delta^2
#
# with z[0.025] = 1.96 and z[0.20] = 0.84:
#
#     2 * (1.96 + 0.84)^2  =  2 * 7.84  =  15.68,  usually rounded to 16
#
# The constant only encodes "how sure do you want to be". All the interesting
# behaviour is in sigma^2 / delta^2: the ratio of noise to signal, SQUARED.
POWER_CONST = 15.68

# Doctors inside one practice share protocols, cover each other's patients and
# talk to each other. A held-out doctor sitting next to a promoted colleague is
# not a clean control, so real pharma holdouts randomise at territory level.
# That inflates the required sample by a design effect.
#
#     design effect = 1 + (m - 1) * ICC
#
# with m doctors per cluster and ICC the intra-cluster correlation.
CLUSTER_SIZE = 8
ICC = 0.05

# Rough gross revenue per Medicare Part D GLP-1 prescription, used only to
# price the experiment. Deliberately conservative and clearly labelled as an
# assumption rather than a measurement.
REVENUE_PER_RX = 900.0


def n_per_arm(sigma: float, delta: float, design_effect: float = 1.0) -> float:
    return POWER_CONST * (sigma ** 2) / (delta ** 2) * design_effect


def main() -> None:
    panel = pd.read_parquet(config.DATA_PROCESSED / "panel.parquet")
    years = sorted(panel["year"].unique())
    last = years[-1]

    cur = panel[panel["year"] == last]
    sigma = float(cur[OUTCOME].std())
    mean_rx = float(cur[OUTCOME].mean())
    n_doctors = int(cur["npi"].nunique())
    design_effect = 1 + (CLUSTER_SIZE - 1) * ICC

    # Standard deviation of the CHANGE, not the level. If the holdout is
    # analysed as a before/after difference, each doctor is their own control,
    # their permanent characteristics cancel, and the relevant noise is how
    # much they CHANGE rather than how much they prescribe. That is a smaller
    # number, and it makes the experiment dramatically cheaper.
    prev = years[-2]
    w = panel.pivot_table(index="npi", columns="year", values=OUTCOME,
                          observed=True).dropna(subset=[prev, last])
    sigma_change = float((w[last] - w[prev]).std())

    print("=" * 76)
    print("  HOLDOUT EXPERIMENT DESIGN     (designed and priced, not run)")
    print("=" * 76)

    print(f"\n1. THE INPUTS, MEASURED FROM OUR OWN DATA ({last})\n")
    print(f"   doctors in the panel                 {n_doctors:>10,}")
    print(f"   mean prescriptions per doctor        {mean_rx:>10.1f}")
    print(f"   standard deviation (the NOISE)       {sigma:>10.1f}")
    print(f"   cluster size assumed (doctors/terr.) {CLUSTER_SIZE:>10}")
    print(f"   intra-cluster correlation assumed    {ICC:>10.2f}")
    print(f"   design effect from clustering        {design_effect:>10.2f}x")
    print(f"""
   THE NOISE IS THE OBSTACLE. Doctors swing by roughly {sigma:.0f} prescriptions
   from year to year for reasons unrelated to any rep: a new clinic, a
   partner retiring, going part-time. An effect of 5 to 12 Rx has to be
   picked out from inside that.""")

    print(f"\n2. THE SINGLE BIGGEST DESIGN DECISION: WHAT YOU MEASURE\n")
    print(f"   standard deviation of the LEVEL   (how much they prescribe) {sigma:>8.1f}")
    print(f"   standard deviation of the CHANGE  (how much they move)      {sigma_change:>8.1f}")
    print(f"   reduction in noise                                          {1-sigma_change/sigma:>8.1%}")
    print(f"""
   Analysing the holdout as a BEFORE/AFTER CHANGE rather than an after-only
   comparison makes each doctor their own control. Everything permanent
   about them cancels out, and the noise you must beat drops from {sigma:.0f} to
   {sigma_change:.0f}.

   Because sigma is SQUARED in the formula, that reduction cuts the required
   sample by about {1-(sigma_change/sigma)**2:.0%}. Same experiment, same budget,
   far more statistical power, from an analysis choice made in advance.""")

    print(f"\n3. HOW MANY DOCTORS THE EXPERIMENT NEEDS\n")
    print(f"   formula:  n per arm = {POWER_CONST} x sigma^2 / delta^2 x design effect")
    print(f"   (80% power, 5% significance, two-sided)\n")
    print(f"   {'effect to detect':<20}{'% of mean':>11}"
          f"{'n/arm LEVELS':>15}{'n/arm CHANGE':>15}")
    print(f"   {'-'*61}")
    rows = []
    for pct in (0.20, 0.10, 0.05, 0.025, 0.01):
        delta = mean_rx * pct
        n_lvl = n_per_arm(sigma, delta, design_effect)
        n_chg = n_per_arm(sigma_change, delta, design_effect)
        rows.append((pct, delta, n_chg))
        flag = "" if n_chg * 2 <= n_doctors else "  X"
        print(f"   {delta:>8.1f} Rx{'':<10}{pct:>10.1%}{n_lvl:>15,.0f}{n_chg:>15,.0f}{flag}")
    print(f"   {'-'*61}")
    print(f"   the whole panel has {n_doctors:,} doctors, which caps what is possible")
    print(f"   (X marks designs too large even for the entire population)")

    print(f"""
   HALVE THE EFFECT, QUADRUPLE THE SAMPLE. delta is SQUARED in the
   denominator, so chasing smaller effects gets expensive very fast. This
   is why "we will measure whether this delivers a 1% lift" is a promise
   nobody can keep.""")

    print(f"\n4. WHAT IT COSTS\n")
    print(f"   If promotion works, every held-out doctor is lost sales. That is")
    print(f"   the price of knowing, and it is paid up front.\n")
    print(f"   assumed GROSS revenue per prescription: ${REVENUE_PER_RX:,.0f}")
    print(f"   (an assumption, not a measurement. Net of the rebates typical in")
    print(f"   this category it would be roughly a third of that, so read these")
    print(f"   costs as an upper bound.)\n")
    print(f"   {'effect to detect':<20}{'holdout size':>14}{'Rx forgone':>14}{'cost':>16}")
    print(f"   {'-'*64}")
    for pct, delta, n in rows:
        if n * 2 > n_doctors:
            continue
        forgone = n * delta
        print(f"   {delta:>8.1f} Rx{'':<10}{n:>14,.0f}{forgone:>14,.0f}"
              f"{'$' + format(forgone * REVENUE_PER_RX / 1e6, ',.1f') + 'M':>16}")
    print(f"   {'-'*64}")

    # the answer an executive actually needs
    best = min((n for _, _, n in rows if n * 2 <= n_doctors), default=None)
    mde = None
    for pct, delta, n in rows:
        if n * 2 <= n_doctors:
            mde = (pct, delta, n)
    print(f"\n5. THE ANSWER TO GIVE AN EXECUTIVE\n")
    if mde:
        pct, delta, n = mde
        print(f"   smallest effect detectable with this population:")
        print(f"     {delta:.1f} Rx per doctor per year  ({pct:.1%} lift)")
        print(f"     needs {n:,.0f} doctors per arm, {n*2:,.0f} in total")
        print(f"     costs about ${n*delta*REVENUE_PER_RX/1e6:,.1f}M in forgone sales")
        print(f"     reads in 2 to 3 quarters, since prescribing responds slowly")
    print(f"""
   AND THE PART THAT SAVES MONEY: anything smaller than that cannot be
   measured at any price this population allows. If someone asks for a 1%
   lift to be proven, the answer is that it would need
   {n_per_arm(sigma, mean_rx*0.01, design_effect):,.0f} doctors per arm, which is more than exist.
   Say so before the budget is approved, not after.

6. WHY THIS DESIGN, AND NOT MORE ANALYSIS

   Every observational method in this repository was tried first:

     naive comparison        56.5 Rx    no correction at all
     PSM                     10.0 Rx    fixes measured differences
     DiD                     11.7 Rx    fixes stable hidden differences
     PSM + DiD                8.1 Rx    fixes both
     trend-adjusted           5.2 Rx    removes pre-existing divergence
     uplift ranking          FAILED     Qini negative, worse than random

   The average effect survives all of it at roughly 5 to 12 Rx. The
   PER-DOCTOR effect does not survive at all.

   That is not a modelling problem to be solved with a better algorithm.
   Reps target doctors whose prescribing is already accelerating, so the
   thing that predicts targeting is the thing that predicts the outcome.
   Randomisation is the only instrument that breaks that link.

   WHAT THE HOLDOUT WOULD UNLOCK, in order:
     1. an unbiased average effect, with a confidence interval
     2. clean training data for the uplift model, so the ranking can be
        learned from randomised exposure instead of rep judgement
     3. a targeting rule that is safe to act on

   CAVEATS ON THIS DESIGN, stated because they change the numbers:
     * sigma is measured on Medicare Part D only, so it excludes commercial
       insurance and understates each doctor's true volume
     * the intra-cluster correlation of {ICC} is an assumption. A real design
       would estimate it from the company's own territory structure.
     * revenue per prescription is a placeholder for pricing only""")
    print("=" * 76)


if __name__ == "__main__":
    main()
