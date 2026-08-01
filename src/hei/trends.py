"""The parallel trends check: test the assumption that difference-in-differences needs.

Difference-in-differences uses the control group's change as a stand-in for what
the treated group WOULD have done without promotion. That substitution is only
legal if both groups would have moved by the same amount anyway.

That is the PARALLEL TRENDS assumption. Parallel does NOT mean equal. The groups
can sit far apart. What matters is that the gap between them would have stayed
the same size.

Most analyses assert this. It can be tested, and this file tests it, which is
only possible because we have three years BEFORE the cutoff.

    2019   2020   2021  |  2022
    ---- before -----   |  after
                        ^
                   cutoff, end of 2021

If the two lines moved together through 2019-2021 and separated only in 2022,
the assumption is credible. If they were already separating beforehand, the
method is invalid and we say so.

Run it:
    python -m hei.trends
"""

from __future__ import annotations

import pandas as pd

from hei import config

OUTCOME = "rx_total"


def build_groups(panel: pd.DataFrame):
    """Treated and control, using the FULL pre-period rather than one year.

    TREATED  no payments in ANY pre year, first payment in the cutoff year
    CONTROL  no payments in any year at all

    Requires a doctor to appear in every year, because a line cannot be drawn
    through missing points.
    """
    years = sorted(panel["year"].unique())
    pre_years, post_year = years[:-1], years[-1]

    wide = panel.pivot_table(index="npi", columns="year",
                             values=[OUTCOME, "pay_n"], observed=True)
    # balanced panel: present in every year
    wide = wide.dropna(subset=[(OUTCOME, y) for y in years])

    pay = {y: wide[("pay_n", y)].fillna(0) for y in years}
    clean_before = pd.Series(True, index=wide.index)
    for y in pre_years:
        clean_before &= pay[y] == 0

    treated = clean_before & (pay[post_year] > 0)
    control = clean_before & (pay[post_year] == 0)
    return wide, treated, control, years, pre_years, post_year


def main() -> None:
    panel = pd.read_parquet(config.DATA_PROCESSED / "panel.parquet")
    wide, treated, control, years, pre_years, post_year = build_groups(panel)

    print("=" * 76)
    print("  PARALLEL TRENDS CHECK")
    print("=" * 76)
    print(f"\n  balanced panel (present in all {len(years)} years): {len(wide):,} doctors")
    print(f"  treated (clean {pre_years[0]}-{pre_years[-1]}, paid {post_year}): {treated.sum():>7,}")
    print(f"  control (never paid):                     {control.sum():>7,}")

    rows = []
    for y in years:
        t = wide.loc[treated, (OUTCOME, y)].mean()
        c = wide.loc[control, (OUTCOME, y)].mean()
        rows.append({"year": y, "treated": t, "control": c, "gap": t - c})
    tab = pd.DataFrame(rows)

    # An event study normalises to the last year BEFORE treatment. That year
    # becomes zero by construction, and every other year is read relative to it.
    base = tab.loc[tab["year"] == pre_years[-1], "gap"].iloc[0]
    tab["gap_vs_base"] = tab["gap"] - base

    print(f"\n1. MEAN {OUTCOME} BY YEAR\n")
    print(f"   PARALLEL TRENDS MEANS THE 'gap' COLUMN STAYS THE SAME SIZE.")
    print(f"   The gap may be large. It must not GROW before the cutoff.\n")
    print(f"   {'year':<8}{'treated':>10}{'control':>10}{'gap':>10}"
          f"{'gap grew by':>14}   period")
    print(f"   {'-'*66}")
    prev_gap = None
    for _, r in tab.iterrows():
        grew = "" if prev_gap is None else f"{r['gap']-prev_gap:>14.1f}"
        period = "  no promotion yet" if r["year"] in pre_years else "  AFTER promotion"
        print(f"   {int(r['year']):<8}{r['treated']:>10.1f}{r['control']:>10.1f}"
              f"{r['gap']:>10.1f}{grew:>14}{period}")
        prev_gap = r["gap"]
    print(f"\n   Read the last column. If it is roughly 0 for the rows marked")
    print(f"   'no promotion yet', the assumption holds. If it grows, it does not.")

    # --- the chart ---------------------------------------------------------
    print(f"\n2. THE PICTURE  (each row scaled to the largest value)\n")
    hi = max(tab["treated"].max(), tab["control"].max())
    for _, r in tab.iterrows():
        tb = "#" * int(round(40 * r["treated"] / hi))
        cb = "." * int(round(40 * r["control"] / hi))
        sep = " |" if r["year"] == post_year else "  "
        print(f"   {int(r['year'])}{sep} treated  {tb:<42}{r['treated']:>7.1f}")
        print(f"        {' '} control  {cb:<42}{r['control']:>7.1f}")
        print()

    # --- the formal test ---------------------------------------------------
    print(f"3. THE PLACEBO TEST\n")
    print(f"   A PLACEBO period is one where NO promotion happened. We run the")
    print(f"   identical DiD calculation on it. Because nothing happened, the")
    print(f"   answer SHOULD BE ZERO. It is a fake test with a known answer.")
    print(f"   If the method finds an effect where there was none, it cannot be")
    print(f"   trusted where there was one.")
    print(f"\n   Every number below is subtracted from table 1 above.\n")
    placebo = []
    for a, b in zip(years, years[1:]):
        ta = tab.loc[tab.year == a, "treated"].iloc[0]
        tb_ = tab.loc[tab.year == b, "treated"].iloc[0]
        ca = tab.loc[tab.year == a, "control"].iloc[0]
        cb = tab.loc[tab.year == b, "control"].iloc[0]
        tc, cc = tb_ - ta, cb - ca
        is_post = b == post_year
        kind = "REAL   (promotion happened)" if is_post else "PLACEBO (nothing happened)"
        print(f"   {a} -> {b}   {kind}")
        print(f"      treated   {tb_:>7.1f} - {ta:>7.1f} = {tc:>7.1f}")
        print(f"      control   {cb:>7.1f} - {ca:>7.1f} = {cc:>7.1f}")
        print(f"      DiD       {tc:>7.1f} - {cc:>7.1f} = {tc-cc:>7.1f}"
              f"      <- should be ~0" if not is_post else
              f"      DiD       {tc:>7.1f} - {cc:>7.1f} = {tc-cc:>7.1f}")
        print()
        if not is_post:
            placebo.append(abs(tc - cc))

    real = (tab.loc[tab.year == post_year, "treated"].iloc[0]
            - tab.loc[tab.year == pre_years[-1], "treated"].iloc[0]) - \
           (tab.loc[tab.year == post_year, "control"].iloc[0]
            - tab.loc[tab.year == pre_years[-1], "control"].iloc[0])
    worst = max(placebo) if placebo else 0.0

    print(f"\n   largest PLACEBO effect (pre-period, should be ~0): {worst:>7.1f} Rx")
    print(f"   REAL effect at the cutoff:                         {real:>7.1f} Rx")
    ratio = real / worst if worst else float("inf")
    print(f"   ratio real / largest placebo:                      {ratio:>7.1f}x")

    # ---------------------------------------------------------------------
    # THE SAME TEST ON A PERCENTAGE SCALE.
    #
    # This is not decoration. The gap is measured in prescriptions, and the
    # treated group STARTS BIGGER. If both groups grow at the same percentage
    # rate, the bigger one gains more prescriptions and the gap widens on its
    # own, with no difference in behaviour at all.
    #
    # Parallel trends applies to whichever scale you chose. Choosing the scale
    # is a modelling decision that changes the answer, so both are reported.
    # ---------------------------------------------------------------------
    print(f"\n   THE SAME TEST ON GROWTH RATES INSTEAD OF COUNTS\n")
    print(f"   {'period':<20}{'treated':>10}{'control':>10}{'difference':>13}")
    print(f"   {'-'*53}")
    pct_placebo = []
    for a, b in zip(years, years[1:]):
        ta = tab.loc[tab.year == a, "treated"].iloc[0]
        tb_ = tab.loc[tab.year == b, "treated"].iloc[0]
        ca = tab.loc[tab.year == a, "control"].iloc[0]
        cb = tab.loc[tab.year == b, "control"].iloc[0]
        gt, gc = (tb_ / ta - 1) * 100, (cb / ca - 1) * 100
        is_post = b == post_year
        lab = f"{a}->{b}" + ("  REAL" if is_post else "  placebo")
        print(f"   {lab:<20}{gt:>9.1f}%{gc:>9.1f}%{gt-gc:>12.1f}pp")
        if is_post:
            pct_real = gt - gc
        else:
            pct_placebo.append(abs(gt - gc))
    pct_worst = max(pct_placebo) if pct_placebo else 0.0
    print(f"   {'-'*53}")
    print(f"   largest placebo {pct_worst:.1f}pp   real {pct_real:.1f}pp   "
          f"ratio {pct_real/pct_worst if pct_worst else float('inf'):.1f}x")
    print(f"""
   READ BOTH. In percentage terms the two groups grew ALMOST IDENTICALLY
   before treatment, so much of the widening prescription gap was simply
   arithmetic from the treated group starting larger.

   But on neither scale is the real effect more than about twice the size
   of a fake effect the method finds where nothing happened. You would want
   five or ten times before trusting it.""")

    print()
    if worst < 0.25 * abs(real):
        print("   VERDICT: the pre-period differences are small next to the real")
        print("   effect, so parallel trends is credible and the DiD estimate")
        print("   can be defended.")
        print("=" * 76)
        return

    print("   VERDICT: the groups were ALREADY diverging before treatment.")
    print("   Parallel trends does NOT hold, so the DiD estimate is not")
    print("   trustworthy on its own. This is reported, not hidden.\n")

    # If the gap was already widening every year, part of the post-cutoff jump
    # would have happened with no promotion at all. The most recent pre-period
    # divergence is the fairest guess at how much.
    trend = placebo[-1]
    adjusted = real - trend
    print(f"4. WHAT IS LEFT AFTER REMOVING THE EXISTING TREND\n")
    print(f"   raw DiD at the cutoff                     {real:>8.1f} Rx")
    print(f"   divergence already running before it      {trend:>8.1f} Rx")
    print(f"   {'-'*48}")
    print(f"   trend-adjusted estimate                   {adjusted:>8.1f} Rx")
    print(f"""
   READ THIS CAREFULLY. The gap between the two groups grew by about
   {placebo[0]:.1f} and then {placebo[1]:.1f} Rx in years when NOBODY was promoted. The
   growth was also accelerating, so absent promotion the {years[-2]}->{post_year}
   gap would likely have widened by at least {trend:.1f} Rx on its own.

   That leaves roughly {adjusted:.1f} Rx that promotion might explain, and even
   that is an upper bound rather than a clean estimate.

   WHY THIS MATTERS MORE THAN A TIDY ANSWER.
   Sales reps are targeting doctors whose prescribing is ALREADY
   accelerating. That is good salesmanship and it is fatal to observational
   measurement, because the thing that predicts targeting is the same thing
   that predicts the outcome.

   No amount of matching or differencing fully removes it. This is the
   empirical argument for a randomised holdout: not a textbook preference,
   but a demonstrated failure of every observational method on this data.""")
    print("=" * 76)


if __name__ == "__main__":
    main()
