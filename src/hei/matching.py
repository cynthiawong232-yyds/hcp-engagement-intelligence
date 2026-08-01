"""Propensity Score Matching (PSM): make the two groups comparable, then compare.

The problem PSM solves: promoted doctors and unpromoted doctors are not alike.
Reps deliberately visit heavy prescribers, so the groups differ before any
promotion happens. Comparing them directly measures the reps' choices, not the
promotion.

PSM stops comparing whole groups and instead finds individual PAIRS of doctors
who closely resemble each other, one promoted and one not.

    1. fit a model that predicts the probability of RECEIVING PROMOTION
       (this predicts the treatment, NOT prescriptions)
    2. pair each treated doctor with an untreated doctor of similar score
    3. delete every doctor with no acceptable partner
    4. compare prescribing inside the pairs

WHY LOGISTIC REGRESSION AND NOT XGBOOST.
A more accurate model makes PSM WORSE. If treatment can be predicted perfectly,
every treated doctor scores near 1.00 and every control near 0.00, no pairs can
be formed, and the method collapses. This failure is called loss of overlap.
The model's job is to BALANCE the groups, not to predict well, so it is judged
on covariate balance after matching rather than on AUC.

Run it:
    python -m hei.matching
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hei import config

OUTCOME = "rx_total"

# Only PRE-period information may enter the propensity model. A feature measured
# after the cutoff would already contain the answer, which is leakage.
NUMERIC_FEATURES = ["rx_total", "rx_glp1", "rx_sglt2", "cost_total",
                    "beneficiaries", "n_drugs"]

# A caliper caps how different a matched pair may be, measured in standard
# deviations of the linear propensity score. 0.2 is the convention. Without it,
# a treated doctor with no real counterpart still gets matched to whoever is
# least bad, which quietly reintroduces the bias we are removing.
CALIPER_SD = 0.2
TOP_SPECIALTIES = 12


def build_analysis_sample(panel: pd.DataFrame):
    """One row per doctor: pre-period features, treatment status, post outcome.

    TREATED  no payments in the pre-period, payments in the post-period
    CONTROL  no payments in either period
    dropped  anyone already promoted before the cutoff (no clean 'before')
    """
    years = sorted(panel["year"].unique())
    pre, post = years[-2], years[-1]

    p = panel[panel["year"] == pre].set_index("npi")
    q = panel[panel["year"] == post].set_index("npi")
    both = p.index.intersection(q.index)
    p, q = p.loc[both], q.loc[both]

    treated = (p["pay_n"] == 0) & (q["pay_n"] > 0)
    control = (p["pay_n"] == 0) & (q["pay_n"] == 0)
    keep = treated | control

    df = pd.DataFrame(index=p.index[keep])
    df["treated"] = treated[keep].astype(int)
    for col in NUMERIC_FEATURES:
        df[col] = p.loc[keep, col].astype(float)
    df["specialty"] = p.loc[keep, "specialty"]
    df["y_pre"] = p.loc[keep, OUTCOME].astype(float)
    df["y_post"] = q.loc[keep, OUTCOME].astype(float)
    return df.reset_index(), pre, post


def design_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Features for the propensity model, with specialty one-hot encoded."""
    X = df[NUMERIC_FEATURES].copy()
    # Heavy right skew on every count. log1p keeps logistic regression from
    # being dominated by a handful of enormous prescribers.
    for c in NUMERIC_FEATURES:
        X[c] = np.log1p(X[c].clip(lower=0))
    top = df["specialty"].value_counts().head(TOP_SPECIALTIES).index
    spec = df["specialty"].where(df["specialty"].isin(top), "OTHER")
    return pd.concat([X, pd.get_dummies(spec, prefix="sp", dtype=float)], axis=1)


def standardised_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Standardised mean difference: the standard way to judge balance.

    Below 0.10 in absolute value is the usual threshold for "balanced".
    """
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return 0.0 if pooled == 0 else (a.mean() - b.mean()) / pooled


def balance_table(X: pd.DataFrame, treated: np.ndarray, idx_t=None, idx_c=None):
    """Standardised differences before and after matching, per feature."""
    rows = []
    t_all, c_all = X[treated == 1], X[treated == 0]
    for col in X.columns:
        before = standardised_diff(t_all[col].values, c_all[col].values)
        after = np.nan
        if idx_t is not None:
            after = standardised_diff(X[col].values[idx_t], X[col].values[idx_c])
        rows.append({"feature": col, "smd_before": before, "smd_after": after})
    return pd.DataFrame(rows)


def main() -> None:
    panel = pd.read_parquet(config.DATA_PROCESSED / "panel.parquet")
    df, pre, post = build_analysis_sample(panel)
    X = design_matrix(df)
    t = df["treated"].values

    print("=" * 74)
    print(f"  PROPENSITY SCORE MATCHING    pre {pre}  ->  post {post}")
    print("=" * 74)
    print(f"\n  treated (newly promoted in {post}): {t.sum():>8,}")
    print(f"  control (never promoted):          {(t==0).sum():>8,}")

    n_panel = panel.loc[panel["year"] == post, "npi"].nunique()
    print(f"""
  WHY THE NAIVE NUMBER BELOW IS SMALLER THAN IN hei.confounding.
  That script compared EVERY promoted doctor against every unpromoted one
  in {post} ({n_panel:,} doctors) and got 56.5 Rx.

  This script must exclude doctors who were ALREADY being promoted in {pre},
  because they have no clean "before" period to measure. Those excluded
  doctors are the most heavily promoted and the heaviest prescribers, so
  removing them cuts the naive gap roughly in half on its own.

  Same data, a stricter sample. Both naive numbers are reported so the
  difference is visible rather than surprising.""")

    # --- 1. the propensity score ------------------------------------------
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, C=1.0),
    )
    model.fit(X, t)
    ps = model.predict_proba(X)[:, 1]

    # Matching happens on the LINEAR propensity (the logit), not the raw
    # probability. Probabilities bunch up near 0 and 1, which makes distances
    # there look artificially small.
    logit = np.log(np.clip(ps, 1e-6, 1 - 1e-6) / (1 - np.clip(ps, 1e-6, 1 - 1e-6)))

    print(f"\n1. THE PROPENSITY SCORE  (predicts TREATMENT, not prescriptions)\n")
    print(f"   {'':<10}{'min':>9}{'25%':>9}{'median':>9}{'75%':>9}{'max':>9}")
    for lab, mask in (("treated", t == 1), ("control", t == 0)):
        s = pd.Series(ps[mask])
        print(f"   {lab:<10}{s.min():>9.3f}{s.quantile(.25):>9.3f}"
              f"{s.median():>9.3f}{s.quantile(.75):>9.3f}{s.max():>9.3f}")

    lo = max(ps[t == 1].min(), ps[t == 0].min())
    hi = min(ps[t == 1].max(), ps[t == 0].max())
    on_support = (ps >= lo) & (ps <= hi)
    print(f"\n   overlap region: {lo:.3f} to {hi:.3f}")
    print(f"   doctors inside it: {on_support.sum():,} of {len(ps):,} "
          f"({on_support.mean():.1%})")
    print(f"   NOTE: wide overlap is GOOD here. It means treatment is hard to")
    print(f"   predict, so comparable pairs exist. A near-perfect model would")
    print(f"   push the groups apart and leave nothing to match.")

    # --- 2. match ----------------------------------------------------------
    caliper = CALIPER_SD * logit.std()
    ti = np.where((t == 1) & on_support)[0]
    ci = np.where((t == 0) & on_support)[0]

    nn = NearestNeighbors(n_neighbors=1).fit(logit[ci].reshape(-1, 1))
    dist, pos = nn.kneighbors(logit[ti].reshape(-1, 1))
    ok = dist.ravel() <= caliper
    m_t, m_c = ti[ok], ci[pos.ravel()[ok]]

    print(f"\n2. MATCHING  (nearest neighbour on the linear propensity)\n")
    print(f"   caliper: {caliper:.4f}  ({CALIPER_SD} x SD of the linear score)")
    print(f"   treated doctors matched:   {len(m_t):>8,} of {len(ti):,} "
          f"({len(m_t)/max(len(ti),1):.1%})")
    print(f"   treated doctors discarded: {len(ti)-len(m_t):>8,}  (no partner "
          f"close enough)")

    # --- 3. balance --------------------------------------------------------
    bal = balance_table(X, t, m_t, m_c)
    bal["improved"] = bal["smd_after"].abs() < bal["smd_before"].abs()
    worst = bal.reindex(bal["smd_before"].abs().sort_values(ascending=False).index)

    print(f"\n3. COVARIATE BALANCE  (this, not AUC, is how PSM is judged)\n")
    print(f"   {'feature':<26}{'SMD before':>12}{'SMD after':>12}")
    print(f"   {'-'*50}")
    for _, r in worst.head(9).iterrows():
        print(f"   {r['feature']:<26}{r['smd_before']:>12.3f}{r['smd_after']:>12.3f}")
    n_bad_before = (bal["smd_before"].abs() > 0.10).sum()
    n_bad_after = (bal["smd_after"].abs() > 0.10).sum()
    print(f"   {'-'*50}")
    print(f"   features imbalanced (|SMD| > 0.10):  {n_bad_before} before  ->  "
          f"{n_bad_after} after")

    # --- 4. the estimates --------------------------------------------------
    y_post_t, y_post_c = df["y_post"].values[m_t], df["y_post"].values[m_c]
    y_pre_t, y_pre_c = df["y_pre"].values[m_t], df["y_pre"].values[m_c]

    psm_est = (y_post_t - y_post_c).mean()
    psm_did = ((y_post_t - y_pre_t) - (y_post_c - y_pre_c)).mean()

    naive = (df.loc[df.treated == 1, "y_post"].mean()
             - df.loc[df.treated == 0, "y_post"].mean())
    plain_did = ((df.loc[df.treated == 1, "y_post"].mean() - df.loc[df.treated == 1, "y_pre"].mean())
                 - (df.loc[df.treated == 0, "y_post"].mean() - df.loc[df.treated == 0, "y_pre"].mean()))

    print(f"\n4. FOUR ESTIMATES OF THE SAME THING\n")
    print(f"   {'method':<34}{'estimate':>12}{'vs naive':>11}")
    print(f"   {'-'*57}")
    for lab, v in (("naive (after only, no correction)", naive),
                   ("PSM (matched pairs, after only)", psm_est),
                   ("DiD (growth, unmatched)", plain_did),
                   ("PSM + DiD (matched, growth)", psm_did)):
        print(f"   {lab:<34}{v:>10.1f} Rx{v/naive:>10.1%}")
    print(f"   {'-'*57}")
    print(f"""
   THEY DISAGREE, AND THAT IS THE RESULT.
   Each method corrects a different problem:
     PSM       fixes the groups starting at different levels
     DiD       fixes stable hidden differences, by comparing growth
     PSM+DiD   fixes both, and is the most defensible of the four

   The estimate falls as the correction gets stronger. Reporting that fall
   is more honest than presenting any single number on its own.""")
    print("=" * 74)


if __name__ == "__main__":
    main()
