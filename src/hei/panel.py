"""Turn raw payment and prescribing files into ONE ROW PER DOCTOR PER YEAR.

This is the table every later step reads. Getting it right matters more than
any model choice, because a mistake here is invisible downstream: the models
will happily fit a wrong table and report good numbers.

    payments (many rows per doctor)  --aggregate-->  one row per doctor-year
    prescriptions (one row per drug) --aggregate-->  one row per doctor-year
                                     --join on NPI->  THE PANEL

Two rules that decide the whole design:

1. THE UNIVERSE IS PART D, NOT OPEN PAYMENTS.
   The panel starts from every doctor who prescribed one of our drugs, then
   attaches payments where they exist. Doing it the other way round would
   include only promoted doctors, and the control group would vanish.
   A doctor with no payment row is not missing data. They are a control.

2. VISITS DEFINE THE GROUP, PRESCRIPTIONS ARE THE MEASUREMENT.
   `n_payments` decides promoted versus unpromoted. `rx_*` is what we compare
   between those groups. They are never mixed.

Run it:
    python -m hei.panel
"""

from __future__ import annotations

import pandas as pd

from hei import config

# Promotional channel groupings. About 96% of all rows are Food and Beverage,
# which is the sales rep bringing lunch to get a few minutes of the doctor's
# time. Speaker and consulting payments are far rarer and far larger, and they
# mark a different kind of relationship, so they are counted separately.
SPEAKER_KEYS = ("faculty", "speaker", "consulting")
TRAVEL_KEYS = ("travel", "lodging")


# ---------------------------------------------------------------------------
# the outcome side
# ---------------------------------------------------------------------------

def load_partd(years=None) -> pd.DataFrame:
    """All prescribing rows we have, one row per doctor per drug per year."""
    years = years or config.YEARS
    frames = []
    for year in years:
        for drug in config.DRUGS_WITH_OUTCOME:
            p = config.RAW_PARTD / f"{drug.lower()}_{year}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                if not df.empty:
                    frames.append(df)
    if not frames:
        raise FileNotFoundError("no Part D files found; run `python -m hei.data` first")
    out = pd.concat(frames, ignore_index=True)
    out["Prscrbr_NPI"] = out["Prscrbr_NPI"].astype(str).str.strip()
    return out


def prescribing_by_doctor_year(partd: pd.DataFrame) -> pd.DataFrame:
    """Collapse prescribing to one row per doctor per year.

    Note on a real measurement limit: Part D suppresses any prescriber-drug
    combination with fewer than 11 claims. Low-volume prescribing is therefore
    invisible, not zero. This truncates the bottom of the outcome and is
    recorded in the model card rather than quietly ignored.
    """
    df = partd.copy()
    df["is_glp1"] = df["Brnd_Name"].isin(config.GLP1_DRUGS)
    df["is_sglt2"] = df["Brnd_Name"].isin(config.SGLT2_DRUGS)

    g = df.groupby(["Prscrbr_NPI", "year"], observed=True)
    out = g.agg(
        rx_total=("Tot_Clms", "sum"),
        cost_total=("Tot_Drug_Cst", "sum"),
        beneficiaries=("Tot_Benes", "sum"),
        n_drugs=("Brnd_Name", "nunique"),
        specialty=("Prscrbr_Type", "first"),
        state=("Prscrbr_State_Abrvtn", "first"),
    ).reset_index()

    # class totals, kept separate on purpose
    for label, mask in (("glp1", df["is_glp1"]), ("sglt2", df["is_sglt2"])):
        sub = (df[mask].groupby(["Prscrbr_NPI", "year"], observed=True)["Tot_Clms"]
               .sum().rename(f"rx_{label}").reset_index())
        out = out.merge(sub, on=["Prscrbr_NPI", "year"], how="left")

    # per-brand columns for the two study designs
    for drug in (config.PRIMARY_DRUG, config.LAUNCH_DRUG):
        sub = (df[df["Brnd_Name"] == drug]
               .groupby(["Prscrbr_NPI", "year"], observed=True)["Tot_Clms"]
               .sum().rename(f"rx_{drug.lower()}").reset_index())
        out = out.merge(sub, on=["Prscrbr_NPI", "year"], how="left")

    fill = [c for c in out.columns if c.startswith("rx_")]
    out[fill] = out[fill].fillna(0)
    return out.rename(columns={"Prscrbr_NPI": "npi"})


# ---------------------------------------------------------------------------
# the treatment side
# ---------------------------------------------------------------------------

def load_payments(years=None) -> pd.DataFrame:
    """All promotional payment rows we have, one row per payment."""
    years = years or config.YEARS
    frames = []
    for year in years:
        p = config.RAW_OPENPAY / f"payments_{year}.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p))
    if not frames:
        raise FileNotFoundError("no Open Payments files found; run `python -m hei.data` first")
    out = pd.concat(frames, ignore_index=True)
    out["covered_recipient_npi"] = out["covered_recipient_npi"].astype(str).str.strip()
    # Teaching hospitals have no prescribing NPI and cannot be joined. There are
    # only a handful, and dropping them is recorded rather than silent.
    out = out[out["covered_recipient_type"] != "Covered Recipient Teaching Hospital"]
    return out


def _drug_hit(payments: pd.DataFrame, drug: str) -> pd.Series:
    """True where a payment names this drug in ANY of the five product slots."""
    target = drug.upper()
    hit = pd.Series(False, index=payments.index)
    for i in range(1, 6):
        col = f"name_of_drug_or_biological_or_device_or_medical_supply_{i}"
        if col in payments.columns:
            hit |= payments[col].str.upper().str.strip().eq(target)
    return hit


def promotion_by_doctor_year(payments: pd.DataFrame) -> pd.DataFrame:
    """Collapse payments to one row per doctor per year."""
    df = payments.copy()
    nature = df["nature_of_payment_or_transfer_of_value"].str.lower().fillna("")
    df["is_speaker"] = nature.str.contains("|".join(SPEAKER_KEYS))
    df["is_travel"] = nature.str.contains("|".join(TRAVEL_KEYS))
    df["is_meal"] = nature.str.contains("food")

    g = df.groupby(["covered_recipient_npi", "year"], observed=True)
    out = g.agg(
        pay_n=("total_amount_of_payment_usdollars", "size"),
        pay_usd=("total_amount_of_payment_usdollars", "sum"),
        pay_max=("total_amount_of_payment_usdollars", "max"),
        pay_n_meal=("is_meal", "sum"),
        pay_n_speaker=("is_speaker", "sum"),
        pay_n_travel=("is_travel", "sum"),
        first_pay_date=("date_of_payment", "min"),
        n_manufacturers=("applicable_manufacturer_or_applicable_gpo_making_payment_name",
                         "nunique"),
    ).reset_index()

    # per-brand treatment, so each study design can define its own exposure
    for drug in (config.PRIMARY_DRUG, config.LAUNCH_DRUG):
        sub = df[_drug_hit(df, drug)]
        agg = (sub.groupby(["covered_recipient_npi", "year"], observed=True)
               .agg(**{f"pay_n_{drug.lower()}": ("total_amount_of_payment_usdollars", "size"),
                       f"pay_usd_{drug.lower()}": ("total_amount_of_payment_usdollars", "sum"),
                       f"first_pay_{drug.lower()}": ("date_of_payment", "min")})
               .reset_index())
        out = out.merge(agg, on=["covered_recipient_npi", "year"], how="left")

    return out.rename(columns={"covered_recipient_npi": "npi"})


# ---------------------------------------------------------------------------
# the join
# ---------------------------------------------------------------------------

def build_panel(years=None) -> pd.DataFrame:
    years = years or config.YEARS
    rx = prescribing_by_doctor_year(load_partd(years))
    promo = promotion_by_doctor_year(load_payments(years))

    # LEFT join from prescribing. Doctors with no payment row are controls,
    # not missing data, so their payment counts become 0 rather than NaN.
    panel = rx.merge(promo, on=["npi", "year"], how="left")

    count_cols = [c for c in panel.columns if c.startswith("pay_") and "first" not in c]
    panel[count_cols] = panel[count_cols].fillna(0)

    # the group label used by every later step
    panel["promoted"] = panel["pay_n"] >= config.PROMOTED_MIN_PAYMENTS
    panel["promoted_strict"] = panel["pay_n"] >= config.PROMOTED_MIN_PAYMENTS_SENSITIVITY

    panel = panel.sort_values(["npi", "year"]).reset_index(drop=True)

    # prior-year features, the strongest confounder and the basis of matching.
    # shift(1) inside each doctor's own history, so a value can only ever come
    # from that doctor's PAST. This is the leakage guard.
    for col in ("rx_total", "rx_glp1", "pay_n"):
        panel[f"{col}_prior"] = panel.groupby("npi", observed=True)[col].shift(1)
    panel["rx_trend_prior"] = (
        panel["rx_total_prior"] - panel.groupby("npi", observed=True)["rx_total"].shift(2)
    )
    return panel


def main() -> None:
    panel = build_panel()
    out = config.DATA_PROCESSED / "panel.parquet"
    panel.to_parquet(out, index=False)

    print(f"panel: {len(panel):,} doctor-year rows  ->  {out}")
    print(f"  distinct doctors: {panel['npi'].nunique():,}")
    print(f"  years:            {sorted(panel['year'].unique())}")
    print()
    print(panel.groupby("year", observed=True).agg(
        doctors=("npi", "nunique"),
        promoted=("promoted", "sum"),
        pct_promoted=("promoted", "mean"),
        mean_rx=("rx_total", "mean"),
    ).round(3).to_string())


if __name__ == "__main__":
    main()
