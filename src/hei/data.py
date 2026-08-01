"""Download the two CMS datasets that record the two arrows of the pharma cycle.

    Open Payments  ->  the TREATMENT   (promotional contact with a named doctor)
    Part D         ->  the OUTCOME     (prescriptions that doctor wrote)

Both are public, free, and keyed on the doctor's NPI, which is what makes them
joinable and what makes this project possible without buying IQVIA data.

Design notes, all measured rather than assumed:

  * Both APIs filter server-side by drug name, so we never download the full
    files. The full Open Payments CSV set would be 20-40 GB; filtered to our
    drug list it is a few hundred MB.
  * Part D returns at most 5,000 rows per request. Open Payments returns at
    most 500, whatever limit you ask for. Both paginate by offset.
  * There is no GROUP BY on either API, so aggregation happens locally.
  * Every (drug, year) pair is cached to its own parquet file. Re-running skips
    what already exists, so an interrupted download resumes instead of
    restarting. This matters: the full pull is roughly 12,000 requests.

Run it:
    python -m hei.data                # download everything, resumable
    python -m hei.data --dry-run      # show what would be downloaded
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from hei import config

# --- how hard we push the APIs --------------------------------------------
# Federal open-data endpoints, so we stay polite: a small worker pool and
# exponential backoff rather than hammering.
MAX_WORKERS = 6
MAX_RETRIES = 4
TIMEOUT = 180

PARTD_PAGE = 5000     # measured ceiling
OPENPAY_PAGE = 500    # measured ceiling; asking for more silently returns zero

# Columns we keep. Part D publishes 22 and Open Payments 91; we need a handful.
PARTD_COLUMNS = [
    "Prscrbr_NPI", "Prscrbr_Type", "Prscrbr_State_Abrvtn",
    "Brnd_Name", "Gnrc_Name",
    "Tot_Clms", "Tot_Drug_Cst", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Benes",
]

# The bulk CSV ships 91 columns. These are the ones we keep.
DRUG_NAME_COLUMNS = [
    f"Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_{i}" for i in range(1, 6)
]

OPENPAY_CSV_COLUMNS = [
    "Covered_Recipient_Type",
    "Covered_Recipient_NPI",
    "Covered_Recipient_Specialty_1",
    "Recipient_State",
    "Total_Amount_of_Payment_USDollars",
    "Number_of_Payments_Included_in_Total_Amount",
    "Date_of_Payment",
    "Nature_of_Payment_or_Transfer_of_Value",
    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name",
    *DRUG_NAME_COLUMNS,
]


def _get_json(url: str):
    """GET a URL and parse JSON, retrying with exponential backoff."""
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                return json.loads(r.read())
        except Exception as ex:      # noqa: BLE001 - any network error is retryable
            last = ex
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {MAX_RETRIES} attempts: {url[:120]}") from last


# ---------------------------------------------------------------------------
# Part D: the OUTCOME
# ---------------------------------------------------------------------------

def fetch_partd(drug: str, year: int) -> pd.DataFrame:
    """All Part D prescriber rows for one drug in one year.

    One row per prescriber per drug: how many prescriptions they wrote and
    what they cost.
    """
    path = config.RAW_PARTD / f"{drug.lower()}_{year}.parquet"
    if path.exists():
        return pd.read_parquet(path)

    dataset = config.PARTD_DATASETS[year]
    base = f"https://data.cms.gov/data-api/v1/dataset/{dataset}/data"

    rows, offset = [], 0
    while True:
        # NOTE: the filter param name contains square brackets. Build the query
        # with urlencode -- escaping them by hand silently breaks the filter and
        # the API then returns the UNFILTERED dataset, which looks like success.
        q = urllib.parse.urlencode(
            {"filter[Brnd_Name]": drug, "size": PARTD_PAGE, "offset": offset}
        )
        page = _get_json(f"{base}?{q}")
        rows.extend(page)
        if len(page) < PARTD_PAGE:
            break
        offset += PARTD_PAGE

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df[[c for c in PARTD_COLUMNS if c in df.columns]].copy()
        for col in ("Tot_Clms", "Tot_Drug_Cst", "Tot_30day_Fills",
                    "Tot_Day_Suply", "Tot_Benes"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["year"] = year
    df.to_parquet(path, index=False)
    return df


# ---------------------------------------------------------------------------
# Open Payments: the TREATMENT
# ---------------------------------------------------------------------------

def openpay_download_url(year: int) -> str:
    """Look up the bulk CSV url for one reporting year."""
    ds = config.OPENPAY_DATASETS[year]
    meta = _get_json(
        f"https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items/{ds}"
    )
    return meta["distribution"][0]["downloadURL"]


def fetch_openpay_year(year: int, chunksize: int = 250_000) -> pd.DataFrame:
    """All promotional payments for our drug list, for one year.

    One output row per payment: which doctor, what date, how much, what kind.
    A $18.42 "Food and Beverage" row is a sales rep buying the office lunch.

    WHY THIS STREAMS A CSV INSTEAD OF CALLING THE API.
    The Open Payments query API returns at most 500 rows and takes 25-45
    seconds per call, degrading further as the offset grows. Our drug list is
    about 5.2 million payment rows, which is roughly 10,000 calls, or over 80
    hours. Measured, not guessed.

    The bulk file is 3-9 GB per year. We never save it. It is parsed in chunks
    straight off the HTTP response, filtered down to our drugs, and discarded,
    so peak disk usage is only the small parquet we write at the end.

    A drug can appear in any of the five product-name columns, so all five are
    checked rather than only the first.
    """
    path = config.RAW_OPENPAY / f"payments_{year}.parquet"
    if path.exists():
        return pd.read_parquet(path)

    url = openpay_download_url(year)
    wanted = {d.upper() for d in config.ALL_DRUGS}

    keep, scanned, matched = [], 0, 0
    started = time.time()
    reader = pd.read_csv(
        url,
        usecols=lambda c: c in set(OPENPAY_CSV_COLUMNS),
        dtype=str,
        chunksize=chunksize,
        low_memory=False,
        on_bad_lines="skip",
    )
    for i, chunk in enumerate(reader, start=1):
        scanned += len(chunk)
        # Match on any of the five product-name columns.
        hit = pd.Series(False, index=chunk.index)
        for col in DRUG_NAME_COLUMNS:
            if col in chunk.columns:
                hit |= chunk[col].str.upper().str.strip().isin(wanted)
        sel = chunk[hit]
        if not sel.empty:
            keep.append(sel)
            matched += len(sel)
        if i % 8 == 0:
            print(f"    {year}: scanned {scanned:>11,}  kept {matched:>9,}  "
                  f"({(time.time()-started)/60:.1f} min)", flush=True)

    df = pd.concat(keep, ignore_index=True) if keep else pd.DataFrame()
    if not df.empty:
        df.columns = [c.lower() for c in df.columns]
        df["total_amount_of_payment_usdollars"] = pd.to_numeric(
            df["total_amount_of_payment_usdollars"], errors="coerce"
        )
        df["date_of_payment"] = pd.to_datetime(
            df["date_of_payment"], errors="coerce", format="mixed"
        )
        df["year"] = year
    df.to_parquet(path, index=False)
    print(f"  {year}: DONE  scanned {scanned:,} rows, kept {len(df):,}  "
          f"({(time.time()-started)/60:.1f} min)  -> {path.name}", flush=True)
    return df


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def _partd_jobs(years):
    """Part D jobs still to run, skipping anything already cached.

    Outcomes only exist for drugs Part D actually covers. Medicare is barred by
    statute from covering weight-loss drugs, so asking for Zepbound or Saxenda
    prescriptions returns nothing.
    """
    jobs = []
    for year in years:
        for drug in config.DRUGS_WITH_OUTCOME:
            if not (config.RAW_PARTD / f"{drug.lower()}_{year}.parquet").exists():
                jobs.append((drug, year))
    return jobs


def download_all(years=None, dry_run: bool = False) -> None:
    years = list(years or config.YEARS)

    op_years = [y for y in years
                if not (config.RAW_OPENPAY / f"payments_{y}.parquet").exists()]
    pd_jobs = _partd_jobs(years)

    print(f"years: {years}")
    print(f"  open payments: {len(op_years)} year-files to stream {op_years}")
    print(f"  part d:        {len(pd_jobs)} drug-year jobs")
    if dry_run:
        return
    if not op_years and not pd_jobs:
        print("everything is already cached, nothing to do")
        return

    started = time.time()

    # Part D first: it is small and fast, so the panel has an outcome side
    # even if the big streaming download is still running.
    if pd_jobs:
        print("\n--- Part D (API) ---", flush=True)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(fetch_partd, d, y): (d, y) for d, y in pd_jobs}
            for i, fut in enumerate(as_completed(futures), start=1):
                drug, year = futures[fut]
                try:
                    n = len(fut.result())
                    print(f"  [{i:>2}/{len(pd_jobs)}] {drug:<11} {year}  {n:>9,} rows",
                          flush=True)
                except Exception as ex_:      # noqa: BLE001
                    print(f"  [{i:>2}/{len(pd_jobs)}] FAILED {drug} {year}: {ex_}",
                          flush=True)

    # Open Payments: one big streamed file per year, done sequentially so we
    # never have two multi-GB streams competing for the same connection.
    if op_years:
        print("\n--- Open Payments (streamed bulk CSV) ---", flush=True)
        for year in op_years:
            try:
                fetch_openpay_year(year)
            except Exception as ex_:      # noqa: BLE001
                print(f"  {year}: FAILED: {ex_}", flush=True)

    print(f"\nall done in {(time.time()-started)/60:.1f} minutes")
    print(f"open payments -> {config.RAW_OPENPAY}")
    print(f"part d        -> {config.RAW_PARTD}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, nargs="+", default=None,
                    help="which years to pull (default: all six)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the jobs without downloading")
    args = ap.parse_args()
    sys.exit(download_all(years=args.years, dry_run=args.dry_run))
