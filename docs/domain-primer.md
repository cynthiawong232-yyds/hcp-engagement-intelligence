# Domain Primer: Pharma Commercial Analytics

This document explains the industry this project sits in. It assumes no prior knowledge of healthcare or pharmaceuticals.

Every industry term is defined the first time it appears, and again later when it appears again.

---

# Part 1: How the pharma business works

## The one fact that explains everything

In most businesses, one person does three things. They choose the product, they use the product, and they pay for it. You choose a coffee, you drink it, you pay for it.

In prescription drugs, these are **three different people**.

| Role | Who does it |
|---|---|
| Chooses the drug | The doctor |
| Uses the drug | The patient |
| Pays for the drug | The insurance company |

A patient cannot buy a prescription drug. It is not legal. The patient must get a prescription from a doctor first.

A **prescription** is a written order from a doctor that allows a patient to receive a specific drug. The short form used in the industry is **Rx**.

So the patient has no choice. The doctor makes the choice.

This is why a pharmaceutical company does not sell to patients. **It sells to doctors.**

## The full cycle

```
PHARMA COMPANY
  makes the drug
       |
       |  spends money on promotion
       |  (this is the arrow we want to measure)
       v
THE DOCTOR
  chooses the drug
  pays nothing
       |
       |  writes a prescription (Rx)
       |  (this is the arrow we want to predict)
       v
THE PATIENT
  takes the drug
  cannot choose it
       |
       |  brings the prescription to
       v
PHARMACY
  gives out the drug
       |
       v
INSURANCE COMPANY or MEDICARE
  pays the bill
       |
       |  the money returns to
       v
PHARMA COMPANY
```

**Medicare** is the United States government health insurance program for people aged 65 and older. It pays for a very large share of all prescriptions in the country. This matters for us because Medicare publishes its data, and private insurance companies do not.

## Who the customer is

The word the industry uses for the doctor is **HCP**. It stands for **Health Care Professional**.

HCP is slightly wider than "doctor". It also includes nurse practitioners and physician assistants, who can also write prescriptions in most US states. In this project, HCP means "any person who can write a prescription".

There are roughly one million HCPs in the United States. A pharmaceutical company tries to influence them one at a time.

Each HCP has a permanent ID number called an **NPI**. It stands for **National Provider Identifier**. Every healthcare provider in the United States has one, and it never changes.

**An NPI works exactly like a customer ID.** In the retail project, each customer had a customer ID. Here, each doctor has an NPI. This is the key that connects all our data files together.

---

# Part 2: What "promotion" means in pharma

Promotion here does not mean discounts or coupons. Doctors do not pay for the drug, so a discount would mean nothing to them.

Promotion means these activities:

| Activity | What it is |
|---|---|
| **Rep visit** | A salesperson drives to the doctor's office and asks for a few minutes to talk about the drug |
| **Meals** | The salesperson brings lunch for the office staff. This is how they get those few minutes |
| **Speaker program** | The company pays a respected doctor to give a presentation to other doctors |
| **Travel and conferences** | The company pays for a doctor to attend a medical conference |
| **Samples** | Free packages of the drug that a doctor can give to patients |

A **rep** is short for **sales representative**. This is a pharmaceutical company employee whose job is to visit doctors in person.

Important: a rep visit is **not a phone call**. It is not cold calling. A rep physically drives to the medical office, often without a scheduled appointment, and waits for a few minutes of the doctor's time. Reps visit the same doctors repeatedly, for years, and build personal relationships.

The industry word for this sales visit is **detailing**. If you read "the doctor was detailed", it means a rep visited them and talked about the drug.

## Why rep time is the thing we are trying to allocate

A pharmaceutical sales rep is expensive. Salary plus car plus expenses costs well over one hundred thousand dollars per year. One rep can make about eight visits per day.

So the total number of visits a company can make is fixed and limited. The business question is not "should we do promotion". The business question is **"which doctors should get the limited visits we have"**.

That is the decision this project is designed to improve.

---

# Part 3: The problem this project solves

## The question

Does promotion actually cause doctors to write more prescriptions?

This sounds simple. It is not.

## Why it is hard: reps choose where to go

Reps do not visit doctors at random. They are told to visit the doctors who already write the most prescriptions. This is a sensible business rule, and it creates a serious measurement problem.

Look at what happens when you compare the two groups:

| Group | Average prescriptions per year |
|---|---|
| Doctors who received promotion | 100 |
| Doctors who received no promotion | 40 |

It looks like promotion produces 60 extra prescriptions. This conclusion is wrong.

The promoted doctors already wrote more prescriptions **before any promotion happened**. That is exactly why the reps went to them. The gap existed first. The promotion came second.

The technical name for this problem is **confounding**. A confounder is a third factor that affects both the treatment and the outcome. Here, the doctor's existing prescribing volume caused both the promotion (reps chose them) and the high prescription count.

We can also call it **selection bias**, because the groups were selected, not assigned randomly.

## Why it is hard: we can never see the answer

For any single doctor, we see one version of history only.

Dr. Chen received 14 rep visits and wrote 100 prescriptions. We will never know what Dr. Chen would have written with zero visits. That version of Dr. Chen does not exist and cannot be observed.

The unobserved version is called the **counterfactual**. It means "what would have happened instead".

Every method in this project is a different strategy for estimating a counterfactual that we cannot observe.

## The four types of doctor

This is the most useful idea in the project.

**Read this carefully: these four types are not a group you can sort doctors into.** They are a hidden property that each doctor already has, which we can never directly observe. We estimate them in Step 4. See "The group names, untangled" in Part 6 if this becomes confusing later.

Every doctor is one of these four:

| Type | Prescribes if promoted | Prescribes if NOT promoted | What to do |
|---|---|---|---|
| **Sure Thing** | Yes | Yes | Do not promote. They prescribe anyway. Money wasted. |
| **Persuadable** | Yes | No | **Promote. All the value is here.** |
| **Lost Cause** | No | No | Do not promote. They will never prescribe. Money wasted. |
| **Sleeping Dog** | No | Yes | Do not promote. The contact annoys them and reduces prescribing. |

Now look again at the current industry rule: visit the doctors who write the most.

**The doctors who write the most are usually Sure Things.** They prescribe with or without a visit. So the standard targeting rule sends the most expensive resource to the group where it has the least effect.

Finding the Persuadables instead is worth a large amount of money. And finding them is a different question from predicting who prescribes a lot.

## Two questions that sound the same and are not

| Question | Method | Difficulty |
|---|---|---|
| Which doctors will prescribe? | Prediction | Normal. Many portfolios do this. |
| Which doctors prescribe **because of** promotion? | Causal estimation | Hard. Very few portfolios do this. |

The second question is what this project answers.

---

# Part 4: The data

Two public datasets record the two arrows in the cycle diagram. Both are free.

## Dataset 1: Medicare Part D Prescribers

**Part D** is the section of Medicare that pays for prescription drugs.

This file records how much each doctor prescribed. One row looks like this:

```
NPI 1234567890  |  Ozempic  |  2023  |  47 prescriptions  |  $82,400 total cost
```

This is our **outcome**. The outcome is the thing we are trying to explain or change.

In the pharma industry, companies normally buy this information from a data vendor called IQVIA, in a product called **Xponent**. Xponent is expensive and private. Part D is free and public and contains the same kind of information for Medicare patients only.

## Dataset 2: Open Payments

In 2010, the US Congress passed a law requiring pharmaceutical companies to publicly report every payment they make to a doctor. The law was a response to corruption concerns. The public database is called **Open Payments**.

This means a real, dated log of promotional activity exists in public. One row looks like this:

```
CompanyName  |  NPI 1234567890  |  2023-03-14  |  $18.42  |  "Food and Beverage"  |  Ozempic
```

That $18.42 is a sandwich. It records a rep visiting that specific doctor on that specific day to talk about that specific drug.

This is our **treatment**. The treatment is the action whose effect we want to measure.

In industry, this information normally comes from a company's own sales system, usually a product called **Veeva**. That data is private. Open Payments is the free public version.

## Dataset 3: NPPES

**NPPES** is the government registry of all NPI numbers. It gives each doctor's specialty, address, and how long they have been practising.

A **specialty** is the doctor's field of medicine. For diabetes drugs the important specialties are endocrinology (hormone and diabetes specialists), family medicine, and internal medicine.

## How they connect

All three files contain the NPI. We join them on NPI.

```
Part D          ---\
Open Payments   ----+--- join on NPI --->  THE PANEL
NPPES           ---/                        one row per doctor per year
```

A **panel** is a table where each row is one subject observed at one point in time. Here each row is one doctor in one year.

## The columns in the panel

| Column | Where it comes from | What it is |
|---|---|---|
| `npi` | all three | doctor ID, the join key |
| `specialty` | NPPES | endocrinology, family medicine, etc. |
| `state` | NPPES | which US state |
| `years_in_practice` | NPPES | how long they have been a doctor |
| `rx_count` | Part D | **THE OUTCOME.** prescriptions written this year |
| `rx_cost` | Part D | total drug cost |
| `rx_count_prior` | Part D | prescriptions written last year |
| `rx_trend_prior` | Part D | whether they were already growing before promotion |
| `n_payments` | Open Payments | **THE TREATMENT.** number of promotional contacts |
| `payment_dollars` | Open Payments | money spent promoting to them |
| `payment_types` | Open Payments | meals, speaker fees, travel |
| `first_payment_date` | Open Payments | when promotion started for this doctor |
| `competitor_rx` | Part D | do they prescribe competing drugs |

Note carefully: `n_payments` decides which group a doctor is in. `rx_count` is what we compare between the groups. **Visits define the group. Prescriptions are the measurement.**

## How the two groups are created

The panel has no column called "group". We build the group from `n_payments`:

```
promoted   =  n_payments  >  0
unpromoted =  n_payments  == 0
```

Two things about this are decisions, not facts, so we test both.

**The threshold is a decision.** Is one free lunch really "promotion"? We start at more than zero because it is the simplest rule. Then we repeat the whole analysis requiring three or more contacts. If the answer changes, we report that it changed.

**The timing must be separated.** The treatment must happen before the outcome we measure. We never compare payments in 2023 against prescriptions in 2023. A rep may have visited that doctor *because* their prescribing was already rising during that same year. Payments are counted in the earlier period, prescriptions in the later period.

---

# Part 5: The project, step by step

```
STEP 1   BUILD THE PANEL
         join the three files on NPI

STEP 2   CALCULATE THE NAIVE ANSWER
         we build this on purpose, knowing it is wrong

STEP 3   ESTIMATE THE REAL EFFECT, THREE WAYS
         3a  propensity score matching
         3b  difference-in-differences
         3c  a holdout experiment, designed but not run

STEP 4   ESTIMATE THE EFFECT FOR EACH INDIVIDUAL DOCTOR
         uplift model

STEP 5   TURN IT INTO A BUSINESS DECISION
         rank doctors, reallocate rep visits, state the dollar impact

STEP 6   DEPLOY IT
         API and web page
```

## Step 2: the naive answer

We compare the average prescriptions of promoted and unpromoted doctors. We expect a very large difference. We know most of it is confounding, not effect.

We build this deliberately so we can show how much smaller the honest number is.

## Step 3a: Propensity Score Matching

The short form is **PSM**.

**Purpose:** make the two groups comparable before comparing them.

The problem is that promoted doctors average 100 prescriptions and unpromoted doctors average 40. These groups are too different to compare directly.

PSM stops trying to compare the whole groups. Instead it finds individual pairs of doctors who resemble each other closely, and compares inside the pairs.

**The four steps:**

1. Build a model that predicts the probability that a doctor **receives promotion**, using only their characteristics. Note carefully: this model does **not** predict prescriptions. It predicts treatment. Its output is a number between 0 and 1, called the **propensity score**.
2. For each promoted doctor, find an unpromoted doctor with almost the same propensity score. Pair them.
3. Remove every doctor who has no match. We delete data on purpose.
4. Compare prescriptions only inside the matched pairs.

**Step 4 finishes the job. Matching produces an answer by itself:**

```
average prescriptions, matched promoted doctors      78
average prescriptions, their matched partners        62
                                                   ----
PSM estimate of the effect of promotion             +16
```

That is the complete PSM result. Nothing else is needed. Difference-in-differences is a **separate** method that reaches its own answer a different way, not a later stage of this one.

Optionally the two can be combined: run difference-in-differences *inside* the matched pairs. That combined version is the strongest of the three, and we report it alongside the others.

### Why the matched pairs cannot be used as per-doctor answers

Matching works on individual doctors, so it looks like it should produce a per-doctor result. It does not. **A pair gives you two doctors, not a per-doctor answer.**

Here is why, with real numbers:

```
Dr. Chen    (promoted)     95 Rx
Dr. Rivera  (matched)      79 Rx
                          -----
difference                +16
```

Now match Dr. Chen to a different partner who is equally good on every measured variable:

```
Dr. Chen    (promoted)     95 Rx
Dr. Patel   (matched)     118 Rx
                          -----
difference                -23
```

**Same Dr. Chen. An equally valid match. Answers of +16 and -23.**

Individual doctors swing by roughly 60 prescriptions from year to year for reasons unrelated to promotion: a new clinic, a partner retiring, going part-time. A single pair difference contains the random variation of **two** doctors at once, so its own standard deviation is around 85. A result of +16 from one pair cannot be distinguished from zero.

**Matching works only because thousands of pair differences average out.** The random swings cancel and the true average effect survives. One pair means nothing. Ten thousand pairs mean something.

Three further reasons pairs cannot replace a model:

| Problem | Detail |
|---|---|
| **Coverage** | Every doctor without a match was deleted, including the entire top decile. They receive no number at all. |
| **New doctors** | Next quarter a doctor appears with no partner. Matching has nothing to say. A trained model can score anyone. |
| **No rule** | A pair gives a difference. A model gives a function, such as "mid-volume endocrinologists in years 3 to 8 of practice respond most". That can be inspected with SHAP and explained to a stakeholder. |

Short version: **matching gives pairs, not per-doctor estimates, and a pair difference is mostly noise until it is averaged.**

**An example pair:**

```
Dr. Chen     endocrinologist, Texas,   95 prescriptions last year, 12 years practising
             propensity score 0.87     PROMOTED

Dr. Rivera   endocrinologist, Arizona, 92 prescriptions last year, 14 years practising
             propensity score 0.85     NOT PROMOTED
```

These two doctors look the same in every way we can measure. One received visits and one did not, for accidental reasons: a sales territory boundary, a rep who left the company, a scheduling problem. Comparing these two is meaningful.

**Why a score instead of matching the raw variables directly:** with twenty variables you will never find an exact twin for any doctor. The propensity score compresses all twenty variables into one number. Matching on that one number balances all twenty variables across the groups on average. That compression is the idea behind the method.

### Which model computes the propensity score, and why it is not XGBoost

The natural guess is XGBoost. It is the wrong choice here, for a reason that is worth understanding.

**A more accurate model makes propensity score matching worse.**

Suppose the model predicts treatment perfectly. Then every promoted doctor receives a score near 1.00, and every unpromoted doctor receives a score near 0.00. No promoted doctor now has a partner with a similar score. **Perfect prediction destroys every pair.** The name for this problem is loss of overlap.

The job of the propensity model is not to predict well. Its job is to **balance the two groups**.

| Role | Choice |
|---|---|
| Primary model | Logistic regression |
| Robustness check | XGBoost, with the score distribution inspected for overlap |
| How we judge it | Covariate balance after matching, **not** AUC |

Covariate balance means: after pairing, is average prior prescribing similar in both groups? Is the specialty mix similar? The usual standard is a standardised mean difference below 0.1.

This is the same lesson as a finding in the retail project, where a silhouette score of 0.925 was worse than 0.372 because the high score came from isolating two outlier customers. A better number, a worse model.

**What the model uses, and what it cannot use:**

| Can measure | Cannot measure |
|---|---|
| Prescriptions last year | The doctor's personal interest in the drug |
| Whether they were already growing | Whether the rep and doctor like each other |
| Specialty | Politics inside the medical practice |
| State, city or rural | Which conference the doctor happened to attend |
| Size of the practice | Whether a colleague already recommends the drug |
| Years practising | |
| Whether they prescribe competing drugs | |

**The weakness of PSM is the right column.** If reps choose partly because a doctor seemed interested when they met, matching on the left column cannot fix it. The technical name is **selection on unobservables**, meaning selection based on things we did not measure.

**A second limitation, which must be stated:** the highest-volume doctors all received promotion. None of them has an unpromoted match, so all of them are deleted in step 3. This means the final estimate describes the middle of the market and not the largest prescribers. The technical name for the region where matches exist is **common support**.

## Step 3b: Difference-in-Differences

The short form is **DiD**.

**Purpose:** remove the starting gap between the groups by comparing growth instead of size.

Consider two years of data:

| | 2022 (before) | 2023 (after) | Change |
|---|---|---|---|
| Promoted doctors | 100 Rx | 112 Rx | **+12** |
| Unpromoted doctors | 40 Rx | 42 Rx | **+2** |

**Comparing sizes** means looking at the 2023 column: 112 against 42. This says promotion is worth 70 prescriptions. This is wrong, because the groups started 60 apart.

**Comparing changes** means looking at the last column: +12 against +2. The estimated effect of promotion is **12 minus 2, which is 10 prescriptions**.

The starting gap of 60 cancels out. That is the idea of the method.

The name describes the arithmetic. The first difference is over time (after minus before). The second difference is between groups (promoted change minus unpromoted change). Difference in differences.

**The assumption this method requires:** we use the unpromoted group's change (+2) as our estimate of what the promoted group would have done with no promotion.

That substitution is only correct if both groups would have changed by the same amount without promotion. This assumption is called **parallel trends**.

**Parallel does not mean equal.** The groups are very unequal, 100 against 40, and that is fine. DiD does not require the groups to be the same size. It requires only that the gap between them would have stayed the same size without promotion. Two lines far apart but rising at the same rate are parallel.

**How this assumption can fail in this project:**

- Endocrinologists write more prescriptions, get more rep attention, and were also increasing their GLP-1 prescribing faster for medical reasons unrelated to reps. DiD would credit promotion for a change in the whole market.
- A skilled rep visits a doctor whose prescribing is already starting to rise. This means the promoted group was already growing faster before any visit. This breaks the parallel trends assumption directly.

**How we check it:** we need more than two time periods. With several years before promotion started, we plot both groups over time.

```
prescriptions
                                        promoted
     ......................____________/
                          /
     ......................____________     unpromoted

     2019    2020    2021    2022    2023
                             ^
                             promotion starts here
```

If the two lines moved together for several years and separated exactly when promotion started, the assumption is believable. If they were already separating before promotion started, DiD is not valid and we report that.

This check is called a **pre-trends test** or an **event study**. Part D data is annual and covers 2013 to 2024, and Open Payments covers 2019 to 2025, so we have six overlapping years and enough history to run it.

### Which model computes DiD

Difference-in-differences is **not a machine learning model**. It is a linear regression.

```
Rx  =  b0
     + b1 (treated)
     + b2 (after)
     + b3 (treated x after)      <-- this coefficient IS the answer
```

The coefficient `b3`, on the interaction of the two indicators, is the estimated effect of promotion. That one number is the whole output.

The better version adds fixed effects:

```
Rx[doctor, year]  =  a[doctor]  +  g[year]  +  b (treated x after)
```

- `a[doctor]` is one intercept per doctor. It absorbs everything permanent about that doctor, including things we never measured.
- `g[year]` is one intercept per year. It absorbs the GLP-1 market growth that affected all doctors.
- `b` is the effect we want.

Library: `linearmodels.PanelOLS`, with standard errors clustered by doctor.

There is no XGBoost anywhere in this step. Causal work usually uses simple models, because the difficulty lives in the study design, not in fitting the curve.

### The hardest problem in this step: every doctor starts at a different time

Standard DiD assumes every treated subject is treated at the same moment. That is not true here. `first_payment_date` differs for every doctor.

This is called **staggered treatment timing**. It is a serious problem, not a detail. Around 2020, economists showed that the standard fixed-effects method gives **biased** results under staggered timing, because doctors treated early are used as control doctors for doctors treated later.

**The design we use, which forces one shared cutoff:**

```
                 2019   2020   2021  |  2022   2023   2024
                 ----- before -----  |  ----- after -----
                                     ^
                            one cutoff for everyone

CONTROL    doctors with ZERO payments in all six years
TREATED    doctors with ZERO payments 2019-2021, first payment in 2022
EXCLUDED   doctors already receiving payments before 2022
```

Now every doctor shares the same cutoff date, and ordinary DiD is valid again.

The cost is that we delete many doctors. We accept that cost and state it clearly.

**Two additional steps:**

- **Event time plot.** Relabel each doctor's years relative to their own first payment: year -2, year -1, year 0, year +1. This uses all doctors and produces the picture that shows whether the lines were parallel before treatment began.
- **Name the modern estimator.** Callaway and Sant'Anna published a method built specifically for staggered timing. Our design above avoids needing it, but knowing why it exists is worth saying.

**A warning about the control group.** Doctors who never receive any payment at all may be unusual: retired, very low volume, or in remote areas. If they are unusual, they are a poor comparison. An alternative control group is "not yet treated" doctors, meaning doctors whose first payment comes later. We check both.

## Step 3c: The holdout experiment

A **holdout** means choosing a random group of doctors and deliberately giving them no promotion. They become the control group. Everyone else receives normal promotion.

This is the same idea as an A/B test. The difference is the situation. In an A/B test you are launching something new and splitting the audience. Here a large operation is already running, and you remove a random group from it.

**Why this method is better than the other two:** random assignment makes the groups comparable on everything, including the things we never measured and never thought about. No parallel trends assumption is needed. No worry about whether we controlled for enough variables.

**Who did the splitting is the key difference between all three methods:**

| Method | Who decided which doctors were promoted |
|---|---|
| Naive comparison | Sales reps, choosing high prescribers on purpose |
| PSM | Sales reps, but we repair the comparison afterwards |
| DiD | Sales reps, but we compare growth so the starting gap cancels |
| **Holdout** | **A random number generator** |

Only the last one is unbiased by design.

**Why pharma companies still avoid holdouts:**

- If promotion works, the company loses those sales. That is a real cost this quarter, paid to learn something.
- Reps resist it, because their income depends on their territory performance.
- **Contamination.** Doctors in the same practice talk to each other and share treatment approaches. A doctor in the holdout group sitting next to a promoted colleague is not a clean control. So companies usually randomise at the practice or territory level rather than the individual doctor level, which reduces the effective sample size.
- Prescribing responds over months. The experiment must run for two or three quarters before it can be read.

**Why we should still recommend it:**

- The promotional budget is being spent either way. The only question is whether anyone knows if it works.
- The holdout is small. A few thousand doctors out of several hundred thousand.
- If promotion does not work, the holdout costs nothing and finds large waste. If promotion does work, the company loses a small amount of sales and gains proof to defend the budget. Both outcomes are useful.

**In this project we do not run a holdout.** We have no reps to command. We **design** one: how many doctors it needs, how much it costs, how long it takes, and which effects are too small to detect at any reasonable price. The design is the deliverable.

The calculation that sizes the experiment is called a **power calculation**. It is documented separately in `docs/power-calculation.md`.

## Step 4: the uplift model

Steps 3a to 3c produce **one average number** for the whole market. Step 4 produces **a different number for every individual doctor**.

**Uplift** means the change in behaviour caused by an action. It is not the same as a prediction of behaviour.

| Model | Question | Example output |
|---|---|---|
| Prediction model | Will this doctor prescribe? | 0.83 probability |
| Uplift model | How many extra prescriptions would a visit cause **for this doctor**? | +3.2 prescriptions |

An uplift output can be zero, meaning do not visit them. It can be negative, meaning visiting them makes things worse.

**How we build it, using the T-learner method:**

```
model A  trained only on promoted doctors     ---\
                                                  >--- difference = uplift
model B  trained only on unpromoted doctors   ---/
```

The letter T stands for "two", because there are two models.

**Neither model predicts uplift.** Both models predict prescriptions. This is worth stating clearly, because it is easy to assume otherwise.

| Model | Trained on | Answers the question |
|---|---|---|
| **Model A** | promoted doctors only | how many prescriptions would this doctor write **if promoted**? |
| **Model B** | unpromoted doctors only | how many prescriptions would this doctor write **if not promoted**? |

Uplift is not a model at all. It is a subtraction performed afterwards:

```
uplift  =  (Model A prediction)  -  (Model B prediction)
```

**The mechanism that makes this work:** we run **both models on every single doctor**, including the doctors we already know were promoted.

Take Dr. Chen, who really was promoted and really wrote 112 prescriptions:

```
Model A says  110    <- close to what really happened, which is reassuring
Model B says  104    <- what she WOULD have written without promotion.
                        this never happened and was never observed.
                        Model B invented it from similar unpromoted doctors.

uplift = 110 - 104 = +6 prescriptions
```

Model B is manufacturing the counterfactual. That is the entire idea of the T-learner.

### What Model A and Model B are trained on

They train directly on the panel. They do **not** train on anything produced in step 3.

```
Model A   training rows = panel rows where promoted == True
          features      = specialty, prior Rx, prior trend, state, tenure, ...
          target        = rx_count

Model B   training rows = panel rows where promoted == False
          features      = the same list
          target        = the same rx_count
```

Neither model sees the propensity score, the matched pairs, or the DiD coefficient.

**One honest addition.** There are respected variants where step 3 *does* feed step 4:

- Train Model A and Model B **on the matched sample only**, instead of the full panel. Less confounding, but less data.
- Use the propensity score as a **weight**. This is called inverse propensity weighting. Combining it with the two outcome models produces the doubly robust family of estimators, including the X-learner.

The basic T-learner does none of this. We build the matched-sample version as a robustness check, because it connects the two halves of the project and tests whether the uplift ranking survives a cleaner training set.

### Step 4 does not depend on step 3

Steps 3a, 3b and 4 are three separate calculations run on the same panel. Nothing flows from one into the next.

```
                  THE PANEL
                      |
        +-------------+-------------+
        |             |             |
      3a PSM       3b DiD       4 UPLIFT
        |             |             |
   one number    one number    one number
    (average)     (average)    PER DOCTOR
```

They are kept together because their strengths are opposite:

- **3a and 3b are more trustworthy.** They are built for causal estimation, with assumptions that can be written down and checked.
- **Step 4 is more useful.** It gives a number for each doctor, which is what a targeting decision requires.

So 3a and 3b act as the **check** on step 4. If the uplift model's per-doctor numbers average to +9 while difference-in-differences says +2, the uplift model is wrong and we must say so.

**How we score it:** not with accuracy, and not with AUC. Those measure prediction quality, and uplift is not a prediction. We use a **Qini curve**, which measures whether the doctors ranked highest by estimated uplift actually showed the largest response. We also report uplift by decile.

**The limitation we must state clearly:** our uplift model is trained on observational data, which means data where reps chose who to visit. It therefore contains the same confounding described in Part 3. Its per-doctor numbers should be treated as a ranking to investigate, not as proven causal effects. The correct next step is to validate the ranking with a real holdout experiment and then retrain the model on that clean data.

## Step 5: the business decision

The output that matters is not a probability. It is a reallocation of rep visits.

The recommendation takes this shape:

> Reps currently spend most of their visits on the highest-volume doctors. Our estimates say those doctors have close to zero uplift, because they prescribe with or without a visit. Moving a share of that rep time to the doctors with the highest estimated uplift would produce an estimated X additional prescriptions per quarter at the same total cost.

A number with a currency sign attached, which changes what people do next week.

---

# Part 6: Every model in one table

Each model in this project is one of two kinds. It either predicts **the treatment** (did this doctor receive promotion?) or **the outcome** (how much did this doctor prescribe?). Sorting them this way removes most of the confusion.

| Step | Model | Predicts | Type | Output |
|---|---|---|---|---|
| 3a | Propensity score | **the treatment** | logistic regression | one score per doctor, used only to build pairs, then discarded |
| 3a | PSM result | the outcome | comparison of matched pairs | **one** average number |
| 3b | DiD | the outcome | linear regression with fixed effects | **one** average number |
| 4 | Model A | the outcome, promoted doctors only | XGBoost | feeds the uplift calculation |
| 4 | Model B | the outcome, unpromoted doctors only | XGBoost | feeds the uplift calculation |
| 4 | Uplift | the outcome | Model A minus Model B | **one number per doctor** |
| later | Rx propensity | the outcome | XGBoost | probability this doctor prescribes at all |

**Only one model in the entire project predicts the treatment.** That is the propensity score in step 3a, and it exists purely to build matched pairs. Every other model predicts the outcome.

## How the three methods relate to each other

Steps 3a and 3b are **alternatives**. Each answers the same question using a different assumption. They can also be combined.

| Setup | What it corrects for |
|---|---|
| PSM alone | the two groups start at different levels |
| DiD alone | stable hidden differences between the groups |
| **PSM, then DiD** | both. Match the doctors first, then compare growth inside the matched pairs |

We run all three and report all three numbers. They will disagree. **Reporting the disagreement is the result.**

Step 4 is not an alternative to steps 3a and 3b. It is a different question:

- Steps 3a and 3b answer **"does promotion work on average?"** Their output is one number.
- Step 4 answers **"for which doctors does it work?"** Its output is one number per doctor.

## The group names, untangled

This is the easiest thing in the project to get lost in, because several different fields contribute vocabulary. Read this section whenever the words stop making sense.

### There are only TWO real groups of doctors

```
              ALL DOCTORS IN THE PANEL
                        |
              did they receive any payment?
                   n_payments > 0
                        |
          +-------------+-------------+
          |                           |
      PROMOTED                   UNPROMOTED
```

Each group has three names. All three mean the same doctors.

| Same group | Other names for it |
|---|---|
| **Promoted** | treated, treatment group, exposed |
| **Unpromoted** | control, control group, unexposed |

"Treatment group" and "control group" are the experiment words. They are borrowed from A/B testing. The doctors are identical.

### Difference-in-differences uses TWO splits at the same time

This is the most common place to get lost, because the two splits sound similar and are completely different.

| Split | Question | Decided by |
|---|---|---|
| **Split 1: WHO** | promoted or unpromoted? | `pay_n > 0` |
| **Split 2: WHEN** | before or after? | the cutoff year |

**The cutoff is a time boundary, not a group boundary.** It marks where "before" ends and "after" begins. It plays no part in deciding who counts as promoted.

We need it because difference-in-differences measures **change**, and change requires a before and an after.

Combining the two splits gives four boxes, and those four boxes are difference-in-differences:

```
                    BEFORE (2021)     AFTER (2022)
                   +---------------+---------------+
   TREATED         |     74.3      |     111.0     |   change +36.7
   (promoted)      |               |               |
                   +---------------+---------------+
   CONTROL         |     56.3      |      81.3     |   change +25.0
   (unpromoted)    |               |               |
                   +---------------+---------------+
                                                       DiD = +11.7
```

**Both groups are followed across both years.** "Treated" means the same doctors had no payment in 2021 and did have one in 2022. That is one group described over time, not two groups.

### The four types are NOT a third group

Sure Thing, Persuadable, Lost Cause and Sleeping Dog are **a hidden property of each individual doctor**. Every doctor already is one of the four, right now, whether or not anyone promoted to them.

**You can never observe which one.** Observing it would require seeing both branches of history for the same doctor. This is the counterfactual problem again.

The two classifications are **independent**. A promoted doctor may be any of the four. An unpromoted doctor may be any of the four. Knowing a doctor's group tells you nothing about their type.

No model outputs these four labels directly. They are produced in Step 4, from two numbers together:

| Baseline (Model B) | Uplift (A minus B) | Type | Action |
|---|---|---|---|
| High | near zero | **Sure Thing** | do not visit, money wasted |
| Low | large positive | **Persuadable** | **visit them** |
| Low | near zero | **Lost Cause** | do not visit, money wasted |
| Anything | negative | **Sleeping Dog** | do not visit, actively harmful |

### Do we run an A/B test?

No. We have no sales representatives to command.

But PSM and difference-in-differences are both **attempts to imitate an A/B test** using data where nobody randomised anything. That is why they borrow the words treatment and control.

| Method | Who assigned the groups | A real experiment? |
|---|---|---|
| A/B test / holdout | a random number generator | yes |
| PSM | sales reps, then we repair the comparison | no, an imitation |
| DiD | sales reps, then we compare growth instead | no, an imitation |

Step 3c, the holdout, is the only real experiment in the project. We design it and price it, but we do not run it.

### Every name on one page

| Name | What it actually is |
|---|---|
| Promoted = treated = treatment group | doctors with `n_payments > 0`. A real group you can see. |
| Unpromoted = control = control group | doctors with `n_payments = 0`. A real group you can see. |
| Sure Thing / Persuadable / Lost Cause / Sleeping Dog | a hidden type each doctor already has. Never observed. Estimated in Step 4. |
| Matched pairs | a filtered subset of the two real groups. Used only in step 3a. |

## The naming problem you must watch for

The industry uses the word **propensity** for two completely different things.

| Term | Predicts | Used for |
|---|---|---|
| **Propensity score** | the probability of **receiving promotion** | a statistical tool for matching, then discarded |
| **Rx propensity** | the probability of **prescribing** | an actual business prediction shown to stakeholders |

One is about the treatment. One is about the outcome. Same word. They are different rows in the table above.

---

# Part 7: Glossary

| Term | Meaning |
|---|---|
| **Common support** | The range where both promoted and unpromoted doctors exist, so matching is possible. Outside it, no comparison can be made. |
| **Confounding** | A third factor that affects both the treatment and the outcome, making the raw comparison misleading. |
| **Counterfactual** | What would have happened under the other choice. It can never be observed. |
| **Covariate balance** | After matching, whether the two groups look similar on measured variables. The correct way to judge a propensity model. Usually standardised difference below 0.1. |
| **Decile** | Doctors sorted into ten groups by prescribing volume. Decile 10 prescribes the most. Standard industry targeting language. |
| **Detailing** | A sales representative's in-person visit to a doctor to discuss a drug. |
| **DiD** | Difference-in-differences. Compares growth between groups instead of size. |
| **Event time** | Relabelling each doctor's years relative to their own first payment, rather than by calendar year. Used to plot pre-trends when treatment timing varies. |
| **Fixed effects** | One intercept per doctor and one per year in a regression. Absorbs everything permanent about a doctor and everything affecting all doctors in a given year. |
| **GLP-1** | A class of drugs for type 2 diabetes and obesity. Includes semaglutide and tirzepatide. |
| **HCP** | Health Care Professional. Anyone who can write a prescription: doctors, nurse practitioners, physician assistants. |
| **Holdout** | A randomly chosen group deliberately given no promotion, used as a clean control group. |
| **IQVIA** | The main commercial data vendor in pharma. Sells prescribing data. |
| **LAAD** | Longitudinal patient claims data sold by IQVIA. Follows patients over time. |
| **Medicare** | US government health insurance for people 65 and older. |
| **NBE** | Next Best Engagement. A system that decides which doctor to contact next, through which channel, with which message. |
| **NPI** | National Provider Identifier. A permanent unique ID for every US healthcare provider. Works like a customer ID. |
| **NPPES** | The public government registry of NPI numbers, specialties and addresses. |
| **NRx** | New prescriptions only, excluding refills. |
| **Overlap** | Whether promoted and unpromoted doctors have similar propensity scores. If a model predicts treatment too well, overlap disappears and no pairs can be formed. |
| **Panel** | A table with one row per subject per time period. |
| **Parallel trends** | The assumption that two groups would have changed by the same amount without treatment. Required by DiD. |
| **Part D** | The section of Medicare that pays for prescription drugs. |
| **Persistency** | Whether a doctor keeps prescribing a drug over time instead of switching away. |
| **PLTV** | Prescriber Lifetime Value. The expected future prescribing value of one doctor. |
| **Power calculation** | Arithmetic that determines how many subjects an experiment needs to detect an effect of a given size. |
| **PSM** | Propensity Score Matching. Pairs similar doctors so the comparison is fair. |
| **Propensity score** | The probability of **receiving promotion**. A matching tool, not a business prediction. |
| **Qini curve** | The standard way to score an uplift model. Measures whether high-ranked doctors really responded more. |
| **Rep** | Sales representative. A pharma employee who visits doctors in person. |
| **Rx** | A prescription. |
| **Rx propensity** | The probability of **prescribing**. A business prediction. Not the same as a propensity score. |
| **Selection bias** | Error caused by groups being chosen deliberately rather than randomly. |
| **Share of voice** | A company's share of all promotional contact a doctor receives, across all competitors. |
| **Specialty** | A doctor's field of medicine. Endocrinology, family medicine, internal medicine. |
| **Staggered treatment timing** | When subjects are treated at different dates rather than all at once. Breaks standard DiD. Handled here by choosing groups that share one cutoff. |
| **T-learner** | An uplift method using two separate models, one per group, and taking the difference. |
| **TRx** | Total prescriptions, including refills. |
| **Uplift** | The change in behaviour **caused by** an action. Different from predicted behaviour. |
| **Veeva** | The sales software most pharma companies use to record rep visits. |
| **Xponent** | IQVIA's product giving prescribing volume for each individual doctor. The private equivalent of Part D. |

---

# Part 8: The five things that matter most

1. **The doctor is the customer.** The patient cannot choose, and the insurer pays. Everything follows from this.
2. **Reps go where the prescribing volume already is.** So promoted doctors always look better, and most of that difference is selection, not effect.
3. **Predicting who prescribes and estimating who is changed by promotion are different questions.** The first is common. The second is the job. High-volume doctors are usually Sure Things, so promoting them is wasted, even though the industry targets them today.
4. **The counterfactual can never be observed.** Every method here estimates it a different way, and each rests on an assumption that could be wrong.
5. **The three methods will produce different numbers, and that disagreement is the result.** Reporting "the naive estimate said 2.5 times, matching said 1.6 times, difference-in-differences said 1.2 times, and here is why the smallest number is the most honest one" is the point of the project.
