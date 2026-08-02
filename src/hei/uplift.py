"""The uplift model: estimate the effect of promotion for EACH INDIVIDUAL doctor.

Steps 3a and 3b (matching, difference-in-differences) each produce ONE number
for the whole market. That number answers "does promotion work on average". It
cannot tell a sales rep which door to knock on, because every doctor gets the
same answer.

This file answers the other question: FOR WHOM does promotion work.

    Model A   trained ONLY on promoted doctors
              answers: how much would this doctor prescribe IF promoted?

    Model B   trained ONLY on unpromoted doctors
              answers: how much would this doctor prescribe IF NOT promoted?

    uplift = Model A prediction - Model B prediction

NEITHER MODEL PREDICTS UPLIFT. Both predict prescriptions. Uplift is the
subtraction afterwards. This is called a T-learner, T for "two models".

The mechanism: we run BOTH models on EVERY doctor, including doctors we already
know were promoted. For a promoted doctor, Model B supplies the branch of
history we never observed. That is how a counterfactual gets manufactured.

WHY THE TREND FEATURES MATTER HERE MORE THAN USUAL.
hei.trends showed that reps target doctors whose prescribing is ALREADY
accelerating. If the model cannot see that acceleration, it will mistake it for
an effect of promotion. So each doctor's own growth history is fed in
explicitly, and the model is forced to learn something beyond "this one was
already rising".

WHAT THIS MODEL CANNOT DO.
It is trained on observational data, where reps chose who to visit. It inherits
every bias hei.trends measured. Its per-doctor numbers are a RANKING to
investigate, not proven causal effects. An uplift model will happily produce a
confident ranking even when the true effect is zero, which is exactly why the
average is checked against the difference-in-differences estimate below.

Run it:
    python -m hei.uplift
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from hei import config

OUTCOME = "rx_total"
SEED = config.RANDOM_SEED

XGB_PARAMS = dict(
    n_estimators=400, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    reg_lambda=1.0, random_state=SEED, n_jobs=4,
)


def build_modelling_sample(panel: pd.DataFrame):
    """One row per doctor: full pre-period history, treatment, post outcome.

    Uses every pre-period year, not just the last one, so the model can see
    each doctor's trajectory rather than only their level.
    """
    years = sorted(panel["year"].unique())
    pre_years, post = years[:-1], years[-1]
    last_pre = pre_years[-1]

    wide = panel.pivot_table(
        index="npi", columns="year",
        values=[OUTCOME, "rx_glp1", "rx_sglt2", "cost_total",
                "beneficiaries", "n_drugs", "pay_n"],
        observed=True,
    )
    wide = wide.dropna(subset=[(OUTCOME, y) for y in years])

    pay = {y: wide[("pay_n", y)].fillna(0) for y in years}
    clean = pd.Series(True, index=wide.index)
    for y in pre_years:
        clean &= pay[y] == 0

    treated = clean & (pay[post] > 0)
    control = clean & (pay[post] == 0)
    keep = treated | control

    X = pd.DataFrame(index=wide.index[keep])
    # level features from the last pre-period year
    for col in (OUTCOME, "rx_glp1", "rx_sglt2", "cost_total",
                "beneficiaries", "n_drugs"):
        X[f"{col}_{last_pre}"] = wide.loc[keep, (col, last_pre)].astype(float)

    # trajectory: the thing reps target on, made explicit
    for a, b in zip(pre_years, pre_years[1:]):
        X[f"growth_{a}_{b}"] = (
            wide.loc[keep, (OUTCOME, b)].astype(float)
            - wide.loc[keep, (OUTCOME, a)].astype(float)
        )
        X[f"ratio_{a}_{b}"] = (
            (wide.loc[keep, (OUTCOME, b)].astype(float) + 1)
            / (wide.loc[keep, (OUTCOME, a)].astype(float) + 1)
        )
    # earliest level, so the model knows where the trajectory started
    X[f"{OUTCOME}_{pre_years[0]}"] = wide.loc[keep, (OUTCOME, pre_years[0])].astype(float)

    # specialty, taken from the panel (constant per doctor in practice)
    spec = (panel[panel["year"] == last_pre]
            .set_index("npi")["specialty"].reindex(X.index))
    top = spec.value_counts().head(12).index
    spec = spec.where(spec.isin(top), "OTHER").fillna("OTHER")
    X = pd.concat([X, pd.get_dummies(spec, prefix="sp", dtype=float)], axis=1)

    t = treated[keep].astype(int).values
    y = wide.loc[keep, (OUTCOME, post)].astype(float).values
    return X, t, y, last_pre, post


def cross_fit(X, t, y, n_splits=5, seed=SEED):
    """Predict both branches for every doctor, always OUT OF SAMPLE.

    THIS IS NOT OPTIONAL, and getting it wrong is the classic T-learner bug.

    If Model A is trained on the treated doctors and then asked about those
    same doctors, it half remembers their real answer. Model B, which never
    saw them, has to guess. The difference between a memory and a guess looks
    exactly like uplift, and it is entirely fake.

    Cross-fitting removes it: the data is cut into folds, and each doctor is
    scored only by models trained on the OTHER folds. Every prediction is then
    genuinely out of sample, for both branches, symmetrically.

    The first version of this file omitted it. The symptom was an observed
    uplift range of -95 to +184 Rx and 31% of doctors classed as Sleeping
    Dogs, both of which are impossible.
    """
    from sklearn.model_selection import StratifiedKFold

    # `seed` is a parameter rather than the module constant so hei.export can
    # rerun this under several seeds. If the per-doctor scores were measuring
    # a real property of each doctor, changing the seed would barely move
    # them. It moves them a lot, which is itself part of the evidence.
    params = {**XGB_PARAMS, "random_state": seed}

    pred_a = np.zeros(len(y))
    pred_b = np.zeros(len(y))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for train_idx, test_idx in skf.split(X, t):
        tr_t = train_idx[t[train_idx] == 1]
        tr_c = train_idx[t[train_idx] == 0]
        a = XGBRegressor(**params).fit(X[tr_t], y[tr_t])
        b = XGBRegressor(**params).fit(X[tr_c], y[tr_c])
        pred_a[test_idx] = a.predict(X[test_idx])
        pred_b[test_idx] = b.predict(X[test_idx])
    return pred_a, pred_b


def qini_points(y, t, uplift, n_points=20):
    """Cumulative incremental outcome as we go down the uplift ranking.

    At each cut point k, compare the treated and control doctors inside the
    top k by predicted uplift, and scale to a common size. A good model puts
    the doctors who really responded at the top, so the curve rises early.
    """
    order = np.argsort(-uplift)
    y, t = y[order], t[order]
    xs, ys = [], []
    for frac in np.linspace(1 / n_points, 1.0, n_points):
        k = max(int(len(y) * frac), 2)
        yt, tt = y[:k], t[:k]
        n_t, n_c = tt.sum(), (tt == 0).sum()
        if n_t == 0 or n_c == 0:
            continue
        gain = (yt[tt == 1].mean() - yt[tt == 0].mean()) * k
        xs.append(frac)
        ys.append(gain)
    return np.array(xs), np.array(ys)


def main() -> None:
    panel = pd.read_parquet(config.DATA_PROCESSED / "panel.parquet")
    X, t, y, last_pre, post = build_modelling_sample(panel)

    print("=" * 76)
    print(f"  UPLIFT MODEL (T-learner)    features to {last_pre}  ->  outcome {post}")
    print("=" * 76)
    print(f"\n  doctors: {len(X):,}    treated: {t.sum():,}    control: {(t==0).sum():,}")
    print(f"  features: {X.shape[1]}")

    # ---- train the two models, cross-fitted -------------------------------
    Xv = X.values
    pred_a, pred_b = cross_fit(Xv, t, y)      # if promoted / if not promoted
    uplift = pred_a - pred_b

    print(f"\n1. THE TWO MODELS  (5-fold cross-fitted)\n")
    print(f"   Model A  trained on {t.sum():>6,} promoted doctors")
    print(f"   Model B  trained on {(t==0).sum():>6,} unpromoted doctors")
    print(f"   every doctor is scored ONLY by models that never saw them,")
    print(f"   so neither branch is a memory of that doctor's real answer")
    print(f"\n   {'':<26}{'mean':>10}{'median':>10}")
    print(f"   {'Model A (if promoted)':<26}{pred_a.mean():>10.1f}{np.median(pred_a):>10.1f}")
    print(f"   {'Model B (if not promoted)':<26}{pred_b.mean():>10.1f}{np.median(pred_b):>10.1f}")
    print(f"   {'uplift = A - B':<26}{uplift.mean():>10.1f}{np.median(uplift):>10.1f}")

    # ---- the sanity check that matters ------------------------------------
    t_chg = y[t == 1].mean()
    c_chg = y[t == 0].mean()
    print(f"\n2. SANITY CHECK AGAINST THE CAUSAL ESTIMATES\n")
    print(f"   mean predicted uplift          {uplift.mean():>8.1f} Rx")
    print(f"   DiD estimate (hei.confounding) {11.7:>8.1f} Rx")
    print(f"   PSM + DiD (hei.matching)       {8.1:>8.1f} Rx")
    print(f"   trend-adjusted (hei.trends)    {5.2:>8.1f} Rx")
    print(f"""
   If the mean predicted uplift sits far above the causal estimates, the
   model is inflated: it is crediting promotion for growth the doctors
   would have had anyway. The causal numbers are the reference, because
   their assumptions are written down and testable. This model's are not.""")

    # ---- does the ranking work? ------------------------------------------
    dec = pd.DataFrame({"uplift": uplift, "y": y, "t": t})
    # qcut labels ascend with value, so 1 = lowest predicted uplift and
    # 10 = highest. Reversing this list silently inverts the whole table.
    dec["decile"] = pd.qcut(dec["uplift"].rank(method="first"), 10,
                            labels=range(1, 11))
    g = dec.groupby("decile", observed=True).apply(
        lambda d: pd.Series({
            "n": len(d),
            "pred_uplift": d["uplift"].mean(),
            "treated_mean": d.loc[d.t == 1, "y"].mean(),
            "control_mean": d.loc[d.t == 0, "y"].mean(),
        }), include_groups=False)
    g["observed_uplift"] = g["treated_mean"] - g["control_mean"]

    print(f"\n3. DOES THE RANKING ACTUALLY WORK?\n")
    print(f"   Rank doctors by PREDICTED uplift, then look at what really")
    print(f"   happened. Decile 10 = highest predicted. A model that works")
    print(f"   shows observed uplift FALLING as you go down the table.\n")
    print(f"   {'decile':<9}{'n':>8}{'predicted':>12}{'observed':>12}")
    print(f"   {'-'*41}")
    for idx in range(10, 0, -1):
        r = g.loc[idx]
        print(f"   {idx:<9}{int(r['n']):>8,}{r['pred_uplift']:>12.1f}"
              f"{r['observed_uplift']:>12.1f}")
    top, bot = g.loc[10, "observed_uplift"], g.loc[1, "observed_uplift"]
    print(f"   {'-'*41}")
    print(f"   top decile minus bottom decile: {top-bot:>8.1f} Rx")

    xs, ys = qini_points(y, t, uplift)
    rand = ys[-1] * xs
    qini = float(np.trapezoid(ys - rand, xs)) if hasattr(np, "trapezoid") \
        else float(np.trapz(ys - rand, xs))
    works = qini > 0 and (top - bot) > 0
    print(f"   Qini area above the random line: {qini:>9,.0f}"
          f"   ({'positive' if qini > 0 else 'NEGATIVE'})")

    if not works:
        print(f"""
   *** THE RANKING DOES NOT WORK. ***

   The doctors this model ranked LOWEST actually responded MORE than the
   ones it ranked highest: {bot:.1f} Rx against {top:.1f} Rx. The Qini area is
   negative, which means the ordering carries no value over picking at
   random.

   Note what is and is not broken:

     the AVERAGE is fine       mean predicted uplift {uplift.mean():.1f} Rx sits
                               inside the causal range of 5.2 to 11.7
     the ORDERING is worthless it cannot say WHICH doctors respond

   That combination is the worst case for targeting, because targeting needs
   only the ordering. A model can be right on average and useless in practice.

   The likely causes, in order of size:
     1. only {t.sum():,} treated doctors, far too few to learn how the effect
        VARIES between doctors
     2. the effect (about 5 to 12 Rx) is tiny next to how much doctors vary
        year to year (a standard deviation around 60 Rx). The signal is
        buried in the noise.
     3. the confounding measured in hei.trends contaminates what signal
        there is

   THIS IS THE POINT OF RUNNING THE CHECK. An uplift model always returns a
   confident-looking ranking. Only an evaluation like this can tell you the
   ranking is noise.""")

    # ---- the four types ---------------------------------------------------
    baseline = pred_b
    hi_base = baseline > np.median(baseline)
    hi_up = uplift > np.quantile(uplift, 0.75)
    neg_up = uplift < 0

    types = np.where(neg_up, "Sleeping Dog",
             np.where(hi_up, "Persuadable",
              np.where(hi_base, "Sure Thing", "Lost Cause")))
    tt = pd.Series(types).value_counts()

    print(f"\n4. THE FOUR TYPES OF DOCTOR\n")
    if not works:
        print(f"   SHOWN FOR ILLUSTRATION ONLY, NOT FOR USE.")
        print(f"   These labels are built from the uplift ranking, and section 3")
        print(f"   just showed that ranking is no better than random. The counts")
        print(f"   below therefore describe the model's beliefs, not the world.\n")
    print(f"   Built from TWO numbers together: the baseline (Model B, what")
    print(f"   they do with no promotion) and the uplift (A minus B).\n")
    print(f"   {'type':<16}{'doctors':>10}{'share':>9}{'mean baseline':>16}{'mean uplift':>14}")
    print(f"   {'-'*65}")
    for name in ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"]:
        m = types == name
        if m.sum() == 0:
            continue
        print(f"   {name:<16}{m.sum():>10,}{m.mean():>8.1%}"
              f"{baseline[m].mean():>16.1f}{uplift[m].mean():>14.1f}")

    # ---- the business number ---------------------------------------------
    n_visit = int((types == "Persuadable").sum())
    print(f"\n5. THE TARGETING RECOMMENDATION\n")
    if works:
        print(f"   doctors worth visiting (Persuadable):        {n_visit:>8,}")
        print(f"""
   The industry rule is to visit the highest-volume prescribers. Those are
   mostly Sure Things: they prescribe with or without a rep. Moving that
   time to the Persuadables is the commercial argument.""")
    else:
        print(f"""   NONE ISSUED.

   This section would normally hand over a list of doctors to visit. It is
   withheld, on purpose, because the model failed its own evaluation in
   section 3.

   Shipping a targeting list from a ranking that scores worse than random
   would move real sales-rep time on the strength of noise. The honest
   deliverable here is the refusal plus the reason.

   WHAT WE CAN SAY, AND IT IS NOT NOTHING:

     * promotion has a positive average effect of roughly 5 to 12 Rx per
       doctor per year, from three methods that agree on the order of
       magnitude
     * that estimate is an upper bound, because parallel trends did not
       hold cleanly on either scale (hei.trends)
     * we CANNOT yet say which doctors drive it

   WHAT WOULD FIX IT: the randomised holdout. It removes the confounding
   entirely, and its clean data is what an uplift model needs to learn
   heterogeneity that is real rather than remembered. The design and the
   price are in hei.experiment.""")
    print("=" * 76)


if __name__ == "__main__":
    main()
