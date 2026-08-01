"""The confounding demonstration: build the wrong answer, then show why it is wrong.

The naive comparison of promoted against unpromoted doctors is the number a
commercial team would reach for first. It is very large and it is mostly false,
because sales reps deliberately visit doctors who already prescribe heavily.

This script produces that number, then takes it apart:

  1. NAIVE       promoted vs unpromoted prescribing, after promotion
  2. PRE-PERIOD  the same doctors BEFORE any promotion happened
  3. DiD         compare growth instead of size
  4. SPLIT       how much of the naive gap was selection, not effect

Run it:
    python -m hei.confounding
"""

from __future__ import annotations

import pandas as pd

from hei import config

OUTCOME = "rx_total"


def _fmt(x: float) -> str:
    return f"{x:>9,.1f}"


def load_panel() -> pd.DataFrame:
    p = config.DATA_PROCESSED / "panel.parquet"
    if not p.exists():
        raise FileNotFoundError("panel not built; run `python -m hei.panel` first")
    return pd.read_parquet(p)


def main() -> None:
    panel = load_panel()
    years = sorted(panel["year"].unique())
    pre, post = years[-2], years[-1]

    print("=" * 74)
    print(f"  pre-period {pre}   post-period {post}   outcome: {OUTCOME}")
    print("=" * 74)
    print(f"""
  TWO SEPARATE SPLITS ARE USED AT THE SAME TIME. They are not the same thing.

    SPLIT 1  WHO    promoted or not      decided by pay_n > 0
    SPLIT 2  WHEN   before or after      decided by the cutoff, end of {pre}

  Combining them gives four boxes, and that IS difference-in-differences:

                        BEFORE ({pre})      AFTER ({post})
                      +----------------+----------------+
      TREATED         |                |                |
      CONTROL         |                |                |
                      +----------------+----------------+

  Both groups are followed across BOTH years. "Treated" means the same
  doctors had no payment in {pre} and did have one in {post}. That is a
  sequence in time for one group, not two different groups.
""")

    # ---------------------------------------------------------------- 1. naive
    after = panel[panel["year"] == post]
    n_pro = after.loc[after["promoted"], OUTCOME]
    n_unp = after.loc[~after["promoted"], OUTCOME]
    naive = n_pro.mean() - n_unp.mean()

    print(f"\n1. THE NAIVE ANSWER  (what a dashboard would report)\n")
    print(f"   promoted doctors     n={len(n_pro):>7,}   mean {_fmt(n_pro.mean())} Rx")
    print(f"   unpromoted doctors   n={len(n_unp):>7,}   mean {_fmt(n_unp.mean())} Rx")
    print(f"   {'difference':<21}{'':>10}      {_fmt(naive)} Rx")
    print(f"   {'ratio':<21}{'':>10}      {n_pro.mean()/n_unp.mean():>9.2f}x")

    # ------------------------------------------------- 2. the same doctors, before
    # A balanced panel: only doctors observed in BOTH years, so the same people
    # are compared to themselves over time.
    wide = panel.pivot_table(index="npi", columns="year",
                             values=[OUTCOME, "pay_n"], observed=True)
    wide = wide.dropna(subset=[(OUTCOME, pre), (OUTCOME, post)])

    pay_pre = wide[("pay_n", pre)].fillna(0)
    pay_post = wide[("pay_n", post)].fillna(0)

    # TREATED: clean before the cutoff, promoted after it.
    # CONTROL: never promoted in either year.
    treated = (pay_pre == 0) & (pay_post > 0)
    control = (pay_pre == 0) & (pay_post == 0)

    t_pre, t_post = wide.loc[treated, (OUTCOME, pre)], wide.loc[treated, (OUTCOME, post)]
    c_pre, c_post = wide.loc[control, (OUTCOME, pre)], wide.loc[control, (OUTCOME, post)]

    print(f"\n2. THE SAME DOCTORS, BEFORE ANY PROMOTION  ({pre})\n")
    print(f"   doctors observed in both years: {len(wide):,}")
    print(f"   treated  (no pay {pre}, paid {post})   n={treated.sum():>7,}   "
          f"mean {_fmt(t_pre.mean())} Rx")
    print(f"   control  (never paid)              n={control.sum():>7,}   "
          f"mean {_fmt(c_pre.mean())} Rx")
    print(f"   {'gap that already existed':<36}      {_fmt(t_pre.mean()-c_pre.mean())} Rx")
    print(f"\n   The gap exists BEFORE the treatment. Nothing has happened yet.")
    print(f"   This is selection, not effect. Reps chose these doctors.")

    # ------------------------------------------------------------------ 3. DiD
    t_change = t_post.mean() - t_pre.mean()
    c_change = c_post.mean() - c_pre.mean()
    did = t_change - c_change

    print(f"\n3. DIFFERENCE-IN-DIFFERENCES  (compare growth, not size)\n")
    print(f"   {'':<12}{pre:>12}{post:>12}{'change':>12}")
    print(f"   {'-'*48}")
    print(f"   {'treated':<12}{t_pre.mean():>12,.1f}{t_post.mean():>12,.1f}{t_change:>12,.1f}")
    print(f"   {'control':<12}{c_pre.mean():>12,.1f}{c_post.mean():>12,.1f}{c_change:>12,.1f}")
    print(f"   {'-'*48}")
    print(f"   {'DiD estimate':<36}      {_fmt(did)} Rx")

    # ----------------------------------------------------------------- 4. split
    print(f"\n4. HOW MUCH OF THE NAIVE ANSWER WAS REAL?\n")
    share = did / naive if naive else float("nan")
    print(f"   naive estimate                           {_fmt(naive)} Rx")
    print(f"   difference-in-differences estimate       {_fmt(did)} Rx")
    print(f"   {'-'*56}")
    print(f"   corrected estimate as a share of naive   {share:>9.1%}"
          f"   ({did:.1f} / {naive:.1f})")
    print(f"   share caused by selection instead        {1-share:>9.1%}")
    print(f"""
   HOW TO READ {did:.1f}:
     a doctor who received promotion wrote about {did:.1f} more prescriptions
     in {post} than that SAME doctor would have written with no rep visit.

     the control group grew by {c_change:.1f} on its own. that is the GLP-1
     market rising, which affected everybody. only the extra {did:.1f} is
     attributable to promotion.

   SELECTION means the reps CHOSE which doctors to visit, and chose the busy
   ones. so the two groups already differed before anything happened.""")

    print(f"\n   LIMITS, printed here so they travel with the number:")
    print(f"     * only {len(years)} years of data, so one pre-period. parallel trends")
    print(f"       cannot be tested yet; that needs 2019 and 2020 as well.")
    print(f"     * Part D deletes any prescriber-drug row under 11 claims for")
    print(f"       privacy. those doctors look like 0 but are really missing.")
    print(f"     * Medicare only. commercial insurance is not in this data.")
    print("=" * 74)


if __name__ == "__main__":
    main()
