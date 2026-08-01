"""Project-wide constants: paths, dataset ids, the drug list, and the study design.

Everything that defines "which doctors, which drugs, which years, which cutoff"
lives here in one place. The most common way a causal project goes wrong is that
two scripts quietly disagree about the study design, so it is defined once and
imported everywhere.
"""

from pathlib import Path

# --- paths -----------------------------------------------------------------
#
# Raw data lives OUTSIDE OneDrive on purpose. Open Payments alone is about
# 5.2 million rows across the study years, and OneDrive would try to sync
# every file. Only the small aggregated panel is written back into the repo.

ROOT = Path(__file__).resolve().parents[2]
DATA_EXTERNAL = Path("C:/data/hcp-nbe")
RAW_PARTD = DATA_EXTERNAL / "raw" / "partd"
RAW_OPENPAY = DATA_EXTERNAL / "raw" / "openpay"
DATA_PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"

for _d in (RAW_PARTD, RAW_OPENPAY, DATA_PROCESSED, ARTIFACTS):
    _d.mkdir(parents=True, exist_ok=True)


# --- the study years -------------------------------------------------------
#
# Part D publishes 2013-2024. Open Payments publishes 2019-2025.
# The overlap is 2019-2024, which is what we use: six years, enough for a
# three-year pre-period and a three-year post-period.

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]


# --- CMS dataset identifiers ----------------------------------------------
#
# CMS mints a new uuid per year rather than exposing a year filter, so these
# are looked up from https://data.cms.gov/data.json and pinned here.

PARTD_DATASETS = {
    2019: "2a6705e6-7a1e-460c-ba22-35249a531918",
    2020: "7795fe20-e80e-435a-a9ed-d2d65e05feeb",
    2021: "f68114ed-f854-4ffc-9c6e-ed78b5e2f8d0",
    2022: "b101b457-ffa4-49bb-8fd9-27c1266086e2",
    2023: "e54db557-cd82-4e91-a0fe-61aad5865d69",
    2024: "d5aa71a8-dcc0-4570-8bcf-bd39deac69fe",
}

OPENPAY_DATASETS = {
    2019: "4e54dd6c-30f8-4f86-86a7-3c109a89528e",
    2020: "a08c4b30-5cf3-4948-ad40-36f404619019",
    2021: "0380bbeb-aea1-58b6-b708-829f92a48202",
    2022: "df01c2f8-dc1f-4e79-96cb-8208beaf143c",
    2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9",
    2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff",
}


# --- the drug list ---------------------------------------------------------
#
# GLP-1 receptor agonists plus the SGLT2 inhibitors that compete for the same
# type 2 diabetes prescribing decision.
#
# IMPORTANT DOMAIN CONSTRAINT, measured rather than assumed:
# Medicare Part D is barred by statute from covering drugs used for weight
# loss. So the obesity-indicated brands have promotional payments but no
# prescribing data. Verified against Part D 2023:
#
#     Ozempic    PRESENT      Zepbound   ABSENT
#     Rybelsus   PRESENT      Saxenda    ABSENT
#     Mounjaro   PRESENT      Victoza    ABSENT (near-zero promotion by 2023)
#     Trulicity  PRESENT
#     Wegovy     PRESENT      (covered on cardiovascular-risk indication)
#     Jardiance  PRESENT
#     Farxiga    PRESENT
#
# We pull payments for all of them, because a doctor promoted for Zepbound is
# still a promoted doctor. We can only measure OUTCOMES for the ones Part D
# actually covers.

DRUGS_WITH_OUTCOME = [
    "Ozempic", "Wegovy", "Rybelsus",   # semaglutide
    "Trulicity",                        # dulaglutide
    "Mounjaro",                         # tirzepatide
    "Jardiance", "Farxiga",             # SGLT2 comparators
]

DRUGS_PROMOTION_ONLY = ["Zepbound", "Victoza", "Saxenda"]

ALL_DRUGS = DRUGS_WITH_OUTCOME + DRUGS_PROMOTION_ONLY

# Two different drug classes, which must not be added together. A GLP-1 and an
# SGLT2 are both type 2 diabetes drugs but they are different mechanisms and
# different competitive sets. Keeping them separate lets us ask whether GLP-1
# promotion grew GLP-1 volume specifically, or just diabetes prescribing overall.
GLP1_DRUGS = ["Ozempic", "Wegovy", "Rybelsus", "Trulicity",
              "Mounjaro", "Zepbound", "Victoza", "Saxenda"]
SGLT2_DRUGS = ["Jardiance", "Farxiga"]


# --- the study design ------------------------------------------------------
#
# Standard difference-in-differences assumes every treated subject is treated
# at the same moment. Doctors are not: each has their own first payment date.
# That problem is called staggered treatment timing, and it biases the usual
# two-way fixed effects estimator.
#
# We avoid it by choosing groups that share one cutoff:
#
#     2019   2020   2021  |  2022   2023   2024
#     ----- before -----  |  ----- after -----
#                         ^
#                    one cutoff for everyone
#
#   CONTROL   zero promotional payments in ALL six years
#   TREATED   zero payments 2019-2021, first payment in 2022
#   EXCLUDED  any doctor already receiving payments before 2022
#
# MOUNJARO LOOKS LIKE THE CLEANEST NATURAL EXPERIMENT, and it half is.
# It launched in 2022, so its payment counts are exactly zero for 2019-2021
# and large from 2022 onward (measured, not assumed):
#
#     2019      0        2022  100,252
#     2020      0        2023  219,402
#     2021      0        2024  231,854
#
# Because the drug did not exist before the cutoff there are no "already
# treated" doctors, so the exclusion rule above costs us nothing.
#
# THE CATCH, which matters: nobody prescribed Mounjaro before 2022 either.
# If the outcome were "Mounjaro prescriptions", both groups would sit at zero
# in the whole pre-period, the first difference would be meaningless, and
# difference-in-differences would collapse into a plain after-only comparison,
# which is the biased thing we are trying to avoid.
#
# So a launch drug forces the outcome to be measured on a scale that existed
# before the launch. Two usable designs, and we run both:
#
#   DESIGN A (launch)     treatment = first Mounjaro payment in 2022
#                         outcome   = the doctor's TOTAL GLP-1 prescribing
#                         question  = did promoting a new GLP-1 grow the
#                                     doctor's whole class volume, or just
#                                     move share between brands?
#
#   DESIGN B (classic)    treatment = first Ozempic payment in 2022,
#                                     excluding anyone paid 2019-2021
#                         outcome   = Ozempic prescriptions
#                         question  = the textbook version, with a real
#                                     pre-period for the same brand

PRE_YEARS = [2019, 2020, 2021]
POST_YEARS = [2022, 2023, 2024]
CUTOFF_YEAR = 2022

PRIMARY_DRUG = "Ozempic"       # design B: has a genuine pre-period
LAUNCH_DRUG = "Mounjaro"       # design A: clean launch, class-level outcome

# A doctor counts as promoted in a year if they received at least this many
# payments. One free lunch is a weak definition of "promoted", so the whole
# analysis is repeated at the sensitivity threshold and any change is reported.
PROMOTED_MIN_PAYMENTS = 1
PROMOTED_MIN_PAYMENTS_SENSITIVITY = 3

RANDOM_SEED = 42
