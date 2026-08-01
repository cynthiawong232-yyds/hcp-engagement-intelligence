# HCP Engagement Intelligence

**Does pharmaceutical promotion actually cause doctors to prescribe more?**

Four causal methods on real public data, plus an uplift model that fails its own evaluation and a randomised experiment designed to fix it.

---

## The headline

The obvious comparison says promotion nearly doubles prescribing. Almost all of that is the sales reps' own targeting decisions, not the promotion.

```
all promoted vs all unpromoted          56.5 Rx      the number a dashboard reports
naive, on a clean sample                29.7 Rx      excluding already-promoted doctors
propensity score matching               10.0 Rx      groups made comparable
difference-in-differences               11.7 Rx      growth compared, not size
PSM + DiD                                8.1 Rx      both corrections at once
trend-adjusted                           5.2 Rx      pre-existing divergence removed

per-doctor uplift ranking              FAILED        Qini negative, worse than random
```

**The average effect is real and small: roughly 5 to 12 extra prescriptions per doctor per year. The per-doctor effect is not recoverable from this data at all.**

That second sentence is the finding. It is why the project ends with an experiment design rather than a targeting list.

---

## Why this is hard

In prescription drugs, three different people do what one person usually does. The **doctor** chooses the drug, the **patient** takes it, the **insurer** pays for it. So pharmaceutical companies market to doctors, one at a time, mostly by sending a sales representative to the office with lunch.

Which doctors get visited is not random. **Reps are sent to the doctors who already prescribe the most.** So promoted doctors always look better, whether or not the visit did anything. That is the confounding this whole project is built to remove.

`docs/domain-primer.md` explains the industry from scratch, assuming no healthcare knowledge.

---

## The data

Real, public, free. No synthetic data anywhere.

| Source | What it records | Industry equivalent |
|---|---|---|
| [CMS Open Payments](https://openpaymentsdata.cms.gov/) | every promotional contact with a named doctor: date, amount, type, drug | Veeva CRM call activity |
| [CMS Medicare Part D Prescribers](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug) | how much each doctor prescribed, per drug, per year | IQVIA Xponent Plantrak |

They join on **NPI**, the doctor's permanent national ID. A typical Open Payments row is a `$15.87` `Food and Beverage` payment: a rep buying the office lunch.

```
scanned    24.9M payment rows across 2019-2022
kept        2.0M rows for GLP-1 and SGLT2 diabetes drugs
panel     487,744 doctor-year rows, 206,024 distinct doctors
```

**Filtered to diabetes and obesity drugs** (semaglutide, tirzepatide, dulaglutide, and SGLT2 comparators), the most consequential category in pharmaceuticals right now.

### Two data facts found by measuring, not assuming

**Medicare cannot pay for weight-loss drugs.** It is barred by statute. So Zepbound and Saxenda have plenty of promotional payments and no prescribing data. Treatment exists, outcome does not.

**A drug launch is only half a natural experiment.** Mounjaro launched in 2022, so its payments are exactly zero beforehand, which looks ideal. But nobody prescribed it beforehand either, so both groups sit at zero through the entire pre-period and difference-in-differences collapses into the biased comparison it was meant to replace. A launch forces the outcome onto a scale that existed before the launch.

---

## How the study is designed

Standard difference-in-differences assumes everyone is treated at the same moment. Doctors are not: each has their own first payment date. That is **staggered treatment timing**, and it biases the usual estimator.

The design forces one shared cutoff instead:

```
2019   2020   2021  |  2022
----- before -----  |  after
                    ^
             one cutoff for everyone

TREATED    no payments 2019-2021, first payment in 2022
CONTROL    no payments in any year
EXCLUDED   anyone already promoted before 2022
```

Excluding the already-promoted doctors is what drops the naive estimate from 56.5 to 29.7. They are the heaviest prescribers, and they have no clean "before" to measure.

---

## Findings

### The gap existed before the treatment did

```
   year       treated   control       gap
   2019          53.7      43.9       9.8
   2020          80.1      64.4      15.7
   2021         112.6      90.0      22.7
   2022         152.6     117.8      34.8   <- first year after promotion
```

In 2021, before any of these doctors had received a payment, the future-treated group already prescribed 18 more. Nothing had happened yet.

### The parallel trends test does not cleanly pass

Difference-in-differences relies on the two groups moving together absent treatment. With three pre-treatment years, that can be tested by running the same calculation on periods where nothing happened. Those **placebo** estimates should be zero.

```
period                  LEVELS (Rx)              GROWTH (%)
              treated  control   diff     treated  control    diff
2019->2020      26.4     20.5     5.9      49.2%    46.8%    2.5pp
2020->2021      32.6     25.6     7.0      40.7%    39.7%    1.0pp
2021->2022 REAL 39.9     27.8    12.2      35.5%    30.9%    4.6pp

LEVELS:      largest placebo 7.0 Rx   real 12.2 Rx   ratio 1.7x
PERCENTAGES: largest placebo 2.5pp    real  4.6pp    ratio 1.9x
```

**The scale changes the story, so both are reported.** In prescription counts the groups look clearly divergent. In growth rates they moved almost identically before treatment, and much of the widening gap was arithmetic from the treated group starting larger.

On neither scale is the real effect more than about twice a fake one. You would want five or ten times.

### Matching works, and works because the model is bad

```
feature                  SMD before   SMD after
n_drugs                       0.243       0.001
cost_total                    0.239      -0.003
rx_total                      0.218      -0.000
beneficiaries                 0.189      -0.005

imbalanced (|SMD| > 0.10):   9 before  ->  0 after
```

Nine unbalanced covariates become zero. All 10,411 treated doctors find a partner.

**This works because the propensity model is weak.** Treated doctors average a 0.170 probability of promotion, controls 0.147. Almost identical. A model that predicted well would push the groups apart and leave no pairs to form. In propensity score matching, **strong prediction is evidence the groups cannot be compared at all**, which is backwards from ordinary machine learning.

Logistic regression, judged on covariate balance rather than AUC.

### The uplift model is right on average and useless in practice

A T-learner: one XGBoost model trained on promoted doctors, another on unpromoted, uplift is the difference. Predictions are **cross-fitted over five folds**, so no doctor is ever scored by a model that saw them.

That detail is not optional. Without it, Model A half-remembers the treated doctors' real answers while Model B has to guess, and the gap between a memory and a guess looks exactly like uplift. The first version of this file omitted cross-fitting and produced an impossible −95 to +184 Rx range.

With it:

```
decile     predicted    observed
10              65.0        48.8
 9              24.0        22.8
 ...
 2              -8.1        10.6
 1             -39.4        90.0

Qini area above random:  -43,510   (NEGATIVE)
```

**The doctors ranked lowest responded the most.** The ordering is worse than random.

| | Verdict |
|---|---|
| The average | fine. 7.4 Rx, inside the causal range of 5.2 to 11.7 |
| The ordering | worthless |

That is the worst combination for targeting, since targeting needs only the ordering. Causes, in order of size: only 2,207 treated doctors to learn variation from; an effect of 5 to 12 Rx sitting inside year-to-year noise with a standard deviation near 64; and the confounding above contaminating what remains.

**`hei.uplift` therefore refuses to output a targeting list.** It prints `NONE ISSUED` and explains why. Shipping a ranking that scores worse than random would move real sales-rep time on the strength of noise.

### The experiment that would settle it

```
effect to detect    n/arm LEVELS   n/arm CHANGE
    17.0 Rx  (20%)         1,384            300
     8.5 Rx  (10%)         5,537          1,200
     4.3 Rx   (5%)        22,149          4,800
     0.9 Rx   (1%)       553,737        119,995   too large to run
```

**Analysing the holdout as a before/after change rather than an after-only comparison cuts the required sample by 78%**, because each doctor becomes their own control and the noise drops from 138 to 64. Same budget, four times the power, from an analysis decision made in advance.

The deliverable for an executive is the last row as much as the first: a 1% lift would need 120,000 doctors per arm, which is more than exist. That is worth saying before the budget is approved rather than after.

---

## Repo layout

```
src/hei/
  config.py        paths, dataset ids, drug list, and the study design in one place
  data.py          stream both CMS sources, filtered to our drugs
  panel.py         one row per doctor per year. the table everything else reads
  confounding.py   the naive answer, built deliberately, then taken apart
  matching.py      propensity score matching, judged on covariate balance
  trends.py        the parallel trends test, on two scales
  uplift.py        T-learner with cross-fitting, and the refusal to ship
  experiment.py    holdout design, power calculation, and the price of knowing
docs/
  domain-primer.md the industry explained from zero
```

Every script prints its own arithmetic and its own limitations, so a number never travels without its caveat.

---

## Quickstart

```bash
python -m venv .venv && .venv/Scripts/activate     # Python 3.11
pip install -r requirements.txt && pip install -e .

python -m hei.data --years 2019 2020 2021 2022     # ~55 min, resumable
python -m hei.panel
python -m hei.confounding
python -m hei.matching
python -m hei.trends
python -m hei.uplift
python -m hei.experiment
```

Raw downloads go to `C:/data/hcp-nbe`, outside the repo, because the source files are 3 to 9 GB per year. Only the filtered panel is kept.

---

## Limitations

Stated here rather than discovered by a reader.

- **Medicare only.** Commercial insurance is absent, so every volume figure understates a doctor's true prescribing.
- **Part D deletes any prescriber-drug row under 11 claims** for privacy. Low-volume prescribing is missing, not zero, and the two cannot be told apart. This truncates exactly where small effects would appear.
- **Parallel trends does not cleanly hold**, so every estimate here is an upper bound.
- **The balanced panel requirement** (a doctor must appear in all four years) selects for consistent prescribers and shrinks the sample from 206,024 to 56,544.
- **Promotion is defined as one payment or more.** The threshold is a decision, not a fact, and the analysis is repeated at three or more.
- **Revenue per prescription is an assumption** used only to price the experiment. Net of rebates it would be roughly a third of the figure used.

## What I would do differently at scale

- **A staggered-adoption estimator.** The single-cutoff design discards every doctor promoted before 2022. Callaway and Sant'Anna's estimator uses them properly and would recover a lot of sample.
- **Territory-level randomisation from the start.** Doctors in one practice share protocols, so individual randomisation leaks. The design effect is assumed here at 1.35 and should be measured.
- **Monthly rather than annual data.** Part D is annual, which is too coarse to see how quickly prescribing responds to a visit, or whether the effect decays.
- **Dose, not a binary.** Fourteen visits and one visit are both "promoted" here. A dose-response curve is the more useful commercial object, and it is what tells you when to stop spending.
