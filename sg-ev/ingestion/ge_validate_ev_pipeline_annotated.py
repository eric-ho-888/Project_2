"""Great Expectations checks for the SG EV charging pipeline (GX Core 1.x).

Validates every layer: raw history -> staging -> star schema -> summary tables, plus
referential integrity (fact -> dimension), derived-column logic and reconciliation
between tables. Results go to Data Docs (HTML) and the script exits 1 on any failure.

Usage
-----
BigQuery (default):
    export BQ_PROJECT=<project that runs the query job and is billed>
    export EV_DATA_PROJECT=sg-ev-510713        # optional, this is the default
    python ge_validate_ev_pipeline.py
CSV folder (for testing without BigQuery): one <key>.csv per table, keys in TABLES below
    python ge_validate_ev_pipeline.py --csv-dir ./sample

Needs great-expectations 1.x and pandas. BigQuery reads also need google-cloud-bigquery,
db-dtypes and pyarrow.

Confirmed from the profile results (13 Oct 2026): the fact, staging and raw tables hold one
row per charging point from the latest load; history holds every load; charger_status only
takes 0 / 1 / 100; current_type is AC or DC. Checks that rest on a reading of the data rather
than a documented rule are marked ASSUMPTION; confirm them in the DataMall API guide.
"""

# ANNOTATED COPY. The logic is identical to ge_validate_ev_pipeline.py; only comments were added.
#
# How to read this file
# ---------------------
# The script has one idea repeated nine times:
#   1. load a table into a pandas dataframe                      (load_* and normalise)
#   2. add True/False "flag" columns for rules that span columns (prepare_*)
#   3. list the expectations (checks) for that table             (suite_*)
#   4. run the checks with Great Expectations and print results  (run_suite, main)
# An "expectation" is one check, for example "column X is never null".
# A "suite" is the list of expectations for one table.

import argparse  # reads command-line options such as --csv-dir
import os  # reads environment variables and joins file paths
import sys  # lets the script return an exit code to the shell

import numpy as np  # NaN (missing value) and vectorised if/else (np.where)
import pandas as pd  # the dataframe library every table is loaded into

import great_expectations as gx  # the GX context, suites and validation objects
import great_expectations.expectations as gxe  # the individual expectation classes

# ----------------------------------------------------------------------------- config
# Everything a rule depends on sits here, so changing a threshold is a one-line edit.

# BigQuery project that holds the data. Can be overridden with the EV_DATA_PROJECT
# environment variable. This is NOT the project that is billed for the queries (BQ_PROJECT).
DATA_PROJECT = os.getenv("EV_DATA_PROJECT", "sg-ev-510713")

# Folder where GX stores its configuration, saved suites and the Data Docs website.
GX_DIR = "gx_ev"

# Name of the GX "data source" that all dataframes are registered under.
SOURCE_NAME = "ev_pipeline_source"

# Short key -> dataset.table. The keys are used everywhere else in the script
# (t["fct"], t["dim"], ...) and as the CSV file names in --csv-dir mode.
TABLES = {
    "raw": "ev_raw.ev_charging_raw",  # latest load as ingested
    "history": "ev_raw.ev_charging_history",  # every load ever ingested
    "staging": "ev_staging.stg_ev_charging",  # cleaned and typed
    "dim": "ev_analytics.dim_ev_charger",  # dimension: one row per charging point
    "fct": "ev_analytics.fct_ev_charging_points",  # fact: status and price per point
    "summary": "ev_analytics.ev_charging_summary",  # summary by region
    "pricing": "ev_analytics.ev_operator_pricing",  # summary by operator
    "region": "ev_analytics.ev_operator_region_analysis",  # summary by operator and region
}

# Column groups used by normalise() to decide how to type each column.
# A column in neither set is treated as a number.
STRING_COLS = {
    "address", "batch_id", "charging_point_name", "current", "current_type", "ev_cp_id",
    "operating_hours", "operator", "plug_type", "position", "postal_code", "price_type",
    "region", "station_name",
}
TIMESTAMP_COLS = {"ingestion_timestamp", "last_updated_time"}

# Rule values. Each one is used by one or more expectations in the suites below.
SG_LAT = (1.15, 1.48)  # latitude bounds that enclose Singapore
SG_LON = (103.6, 104.1)  # longitude bounds that enclose Singapore
STATUS_CODES = [0, 1, 100]  # charger_status: the only values in the data
POINT_STATUS = [0, 1]  # ev_id_status; blank for some points
REGIONS = ["Central", "West", "East", "North-East", "North"]
PRICE_TYPES = ["kWh", "free"]
PRICE_CAP = 2.0  # sanity cap in S$/kWh (highest seen: 0.91); catches unit errors such as cents
DC_PLUGS = ["Combo 2", "CHAdeMO"]  # plug types allowed on DC (fast) chargers
ID_REGEX = r"^R\d{6}[A-Z]-\d{3}$"  # e.g. R123456A-001: R, 6 digits, a letter, dash, 3 digits
POSTAL_REGEX = r"^\d{6}$"  # Singapore postal codes are exactly 6 digits


# ----------------------------------------------------------------------------- loading
def load_bigquery(project: str | None) -> dict:
    # Imported here so CSV mode works even if google-cloud-bigquery is not installed.
    from google.cloud import bigquery

    if os.getenv("EV_AUTH") == "browser":
        # Optional login path when gcloud is not installed: opens a browser once and
        # caches the token. Needs: pip install pydata-google-auth
        import pydata_google_auth

        creds = pydata_google_auth.get_user_credentials(
            ["https://www.googleapis.com/auth/bigquery"], use_local_webserver=True
        )
        client = bigquery.Client(project=project, credentials=creds)
    else:
        # Default path: uses the credentials from `gcloud auth application-default login`
        # (or GOOGLE_APPLICATION_CREDENTIALS). `project` is the job/billing project.
        client = bigquery.Client(project=project)

    # One SELECT * per table, read straight into a dataframe.
    # The result is a dict: {"raw": dataframe, "history": dataframe, ...}.
    return {
        key: client.query(f"SELECT * FROM `{DATA_PROJECT}.{ref}`").to_dataframe()
        for key, ref in TABLES.items()
    }


def load_csv_dir(folder: str) -> dict:
    # Test mode: one <key>.csv per table. dtype=str keeps every value as text,
    # and normalise() then applies the real types, as it would for BigQuery data.
    return {key: pd.read_csv(os.path.join(folder, f"{key}.csv"), dtype=str) for key in TABLES}


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Typed columns for numbers and timestamps, real NaN for blank text, no pandas NA types."""
    df = df.copy()  # never modify the caller's dataframe
    for col in df.columns:
        if col in TIMESTAMP_COLS:
            # errors="coerce": an unparseable value becomes NaT (missing) instead of raising,
            # so it later fails a not-null check rather than crashing the script.
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        elif col in STRING_COLS:
            s = df[col].astype("string").str.strip()  # trim spaces
            keep = s.notna() & (s != "")  # real text, not blank
            # Blank strings become NaN so "not null" treats them as missing.
            df[col] = s.astype(object).where(keep, np.nan)
        else:
            # Everything else is numeric. Non-numeric text becomes NaN, and float64 avoids
            # pandas' special nullable types, which GX handles less predictably.
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


# ----------------------------------------------------------------------------- helpers
# Thin wrappers that keep the suites short. Each returns Great Expectations objects.
def not_null(*cols):
    # Returns a LIST (one expectation per column); suites unpack it with a leading *.
    return [gxe.ExpectColumnValuesToNotBeNull(column=c) for c in cols]


def between(col, lo=None, hi=None, strict_min=False, mostly=1.0):
    # Builds only the bounds that were given, so one helper covers ">= 0", "<= 100"
    # and "between a and b". strict_min=True makes the lower bound exclusive (> 0).
    # mostly=1.0 means 100% of rows must pass.
    kw = {"column": col, "strict_min": strict_min, "mostly": mostly}
    if lo is not None:
        kw["min_value"] = lo
    if hi is not None:
        kw["max_value"] = hi
    return gxe.ExpectColumnValuesToBeBetween(**kw)


def in_set(col, values, mostly=1.0):
    # Value must be one of the allowed list. Missing values are ignored by this check,
    # which is why blank ev_id_status or price_type does not fail it.
    return gxe.ExpectColumnValuesToBeInSet(column=col, value_set=values, mostly=mostly)


def flag(col, mostly=1.0):
    """A derived boolean column that must be True on every row."""
    # This is the key trick: a multi-column rule is computed as a True/False column in
    # pandas (prepare_*), then this asserts that the column is all True.
    # mostly=0.99 would allow 1% of rows to be False, used for rules inferred from the data.
    return gxe.ExpectColumnValuesToBeInSet(column=col, value_set=[True], mostly=mostly)


def same(a: pd.Series, b: pd.Series) -> pd.Series:
    # Plain == treats NaN != NaN, so two blanks would count as different.
    # This treats "both blank" as equal too.
    return (a == b) | (a.isna() & b.isna())


# ----------------------------------------------------------------------------- suites
def suite_layer():
    """Raw history and staging: not empty, keys present, no duplicate (point, load), valid status."""
    # Shared by raw_history and staging, because both have one row per point per load.
    return [
        gxe.ExpectTableRowCountToBeBetween(min_value=1),  # the table is not empty
        *not_null("ev_cp_id", "ingestion_timestamp"),  # the two key columns are present
        # A charging point may appear only once per load. Two columns together form the key.
        gxe.ExpectCompoundColumnsToBeUnique(column_list=["ev_cp_id", "ingestion_timestamp"]),
        in_set("charger_status", STATUS_CODES),  # only 0, 1 or 100
    ]


def prepare_history_batches(history):
    """One row per load: size and completeness, so a partial load shows up."""
    # Collapses the 92,880-row history into one row per batch (load).
    b = (
        history.groupby("batch_id", dropna=True)
        .agg(row_count=("ev_cp_id", "size"), distinct_points=("ev_cp_id", "nunique"))
        .reset_index()
    )
    # True when no charging point is repeated within the load.
    b["no_duplicates_in_batch"] = b["row_count"] == b["distinct_points"]
    # A load much smaller than the biggest one is probably partial.
    b["batch_complete"] = b["row_count"] >= 0.95 * b["row_count"].max()
    return b


def suite_history_batches():
    # Runs on the one-row-per-load table above, not on the raw history itself.
    return [gxe.ExpectTableRowCountToBeBetween(min_value=1), flag("batch_complete")]


def suite_dim(dim):
    # `dim` is accepted for symmetry with the other suites but not used.
    return [
        gxe.ExpectTableRowCountToBeBetween(min_value=1),
        *not_null("ev_cp_id", "operator", "power_rating_kw"),
        gxe.ExpectColumnValuesToBeUnique(column="ev_cp_id"),  # the dimension key
        in_set("current_type", ["AC", "DC"]),
        # mostly=0.99: a format check on inferred patterns warns on a few odd rows
        # instead of failing the whole run.
        gxe.ExpectColumnValuesToMatchRegex(column="ev_cp_id", regex=ID_REGEX, mostly=0.99),
        gxe.ExpectColumnValuesToMatchRegex(column="postal_code", regex=POSTAL_REGEX, mostly=0.99),
    ]


def prepare_fct(fct, dim):
    # Adds the True/False flag columns that the fact-table suite asserts.
    fct = fct.copy()

    # Referential integrity: every fact row points at a dimension row.
    fct["dim_match"] = fct["ev_cp_id"].isin(set(dim["ev_cp_id"].dropna()))

    # Attributes repeated in the fact must agree with the dimension.
    # Step 1: look up the dimension row for each fact row (the _dim suffix marks those columns).
    d = dim.drop_duplicates("ev_cp_id").set_index("ev_cp_id")
    joined = fct.join(d[["operator", "current_type", "power_rating_kw"]], on="ev_cp_id", rsuffix="_dim")
    # Step 2: did the lookup find a row? If not, dim_match already reports it, so
    # this flag is not double-counted.
    found = joined["operator_dim"].notna() | joined["current_type_dim"].notna()
    # Step 3: all three attributes must match. np.isclose compares floats with a tolerance.
    agree = (
        same(joined["operator"], joined["operator_dim"])
        & same(joined["current_type"], joined["current_type_dim"])
        & pd.Series(np.isclose(joined["power_rating_kw"], joined["power_rating_kw_dim"], equal_nan=True),
                    index=joined.index)
    )
    fct["matches_dim"] = (~found) | agree

    # Price and price type come as a pair; "free" means a price of 0.
    # Rule 1: price is blank exactly when price_type is blank.
    # Rule 2: not (price_type is "free" and price is not 0).
    fct["price_pair_ok"] = (fct["price"].isna() == fct["price_type"].isna()) & ~(
        (fct["price_type"] == "free") & (fct["price"] != 0)
    )

    # AC points use Type 2 plugs; DC points use Combo 2 or CHAdeMO.
    # Nested np.where: if AC -> must be Type 2; else if DC -> must be a DC plug; else True.
    fct["plug_matches_current"] = np.where(
        fct["current_type"] == "AC", fct["plug_type"] == "Type 2",
        np.where(fct["current_type"] == "DC", fct["plug_type"].isin(DC_PLUGS), True),
    ).astype(bool)

    # ASSUMPTION: charger_status is the station-level roll-up and ev_id_status is the point's own
    # status. In the data, a point that is itself available always sits in an available station,
    # and a station with status 100 has no point-level status.
    # The flag is True unless one of those two contradictions occurs.
    fct["status_consistent"] = ~(
        ((fct["ev_id_status"] == 1) & (fct["charger_status"] != 1))
        | ((fct["charger_status"] == 100) & fct["ev_id_status"].notna())
    )

    # Operator names are upper case in the source except for one operator; informational.
    # (Computed but not asserted in suite_fct, to keep the suite short.)
    fct["operator_uppercase"] = fct["operator"] == fct["operator"].str.upper()

    # ASSUMPTION: the source's last-updated time is not after the load time.
    # A blank time passes; 5 minutes of tolerance allows for clock differences.
    # (Computed but not asserted in suite_fct.)
    fct["updated_not_after_ingest"] = fct["last_updated_time"].isna() | (
        fct["last_updated_time"] <= fct["ingestion_timestamp"] + pd.Timedelta(minutes=5)
    )
    return fct


def suite_fct():
    # The longest suite: the fact table is where the business rules live.
    return [
        gxe.ExpectTableRowCountToBeBetween(min_value=1),
        *not_null("ev_cp_id", "operator", "charger_status"),
        # The fact table holds the latest load only: one row per charging point.
        gxe.ExpectColumnValuesToBeUnique(column="ev_cp_id"),
        in_set("charger_status", STATUS_CODES),
        in_set("ev_id_status", POINT_STATUS),  # blanks are ignored
        in_set("current_type", ["AC", "DC"]),
        in_set("region", REGIONS),
        in_set("price_type", PRICE_TYPES),  # blanks are ignored
        between("power_rating_kw", 0, strict_min=True),  # power must be above 0
        between("price", 0, PRICE_CAP),  # 0 to 2.0 S$/kWh; blank prices are ignored
        between("latitude", *SG_LAT),  # *SG_LAT unpacks the (low, high) pair
        between("longitude", *SG_LON),
        # The derived flags from prepare_fct, each required to be True on every row
        # (matches_dim allows 1% exceptions).
        flag("dim_match"), flag("matches_dim", mostly=0.99), flag("price_pair_ok"),
        flag("plug_matches_current"), flag("status_consistent"),
    ]


def prepare_summary(s):
    s = s.copy()
    # Total connectors must equal AC plus DC connectors.
    s["total_matches_ac_dc"] = s["total_connectors"] == s["ac_connectors"] + s["dc_connectors"]
    # Available + occupied + unknown can never exceed the total.
    s["status_counts_within_total"] = (
        s["available_connectors"] + s["occupied_connectors"] + s["connectors_with_unknown_status"]
        <= s["total_connectors"]
    )
    # Computed for completeness; not asserted in suite_summary.
    s["incomplete_pricing_within_total"] = s["connectors_with_incomplete_pricing"] <= s["total_connectors"]
    return s


def suite_summary(s):
    # `s` is accepted for symmetry but not used.
    return [
        gxe.ExpectTableRowCountToBeBetween(min_value=1),
        gxe.ExpectColumnValuesToBeUnique(column="region"),  # one row per region
        *not_null("total_connectors"),
        flag("total_matches_ac_dc"), flag("status_counts_within_total"),
    ]


def prepare_price_table(t, positive_col, points_col="charging_points"):
    # Shared by the pricing table and the region table. positive_col is the name of the
    # "points with a positive price" column, which differs between the two tables.
    t = t.copy()
    # Points with a price cannot outnumber all points.
    t["positive_within_points"] = t[positive_col] <= t[points_col]
    # Price order must be min <= average <= max. Rows with no average are skipped.
    bad_order = t["avg_price_per_kwh"].notna() & (
        (t["min_price_per_kwh"] > t["avg_price_per_kwh"]) | (t["avg_price_per_kwh"] > t["max_price_per_kwh"])
    )
    t["price_order_ok"] = ~bad_order
    return t


def suite_price_table(keys, extra=None):
    # keys: the columns that identify a row. ["operator"] for the pricing table,
    # ["operator", "region"] for the region table.
    e = [gxe.ExpectTableRowCountToBeBetween(min_value=1)]
    if len(keys) == 1:
        e.append(gxe.ExpectColumnValuesToBeUnique(column=keys[0]))
    else:
        e.append(gxe.ExpectCompoundColumnsToBeUnique(column_list=keys))
    e += [between("charging_points", 1), flag("positive_within_points"), flag("price_order_ok")]
    return e + (extra or [])  # extra: optional additional expectations


def build_reconciliation(t):
    """One row; each column is a difference that must be 0. Column names read well in Data Docs."""
    fct = t["fct"]
    # The summary tables are built from the latest load, so compare against that load only.
    latest = fct[fct["ingestion_timestamp"] == fct["ingestion_timestamp"].max()]
    # The summary table must account for every charging point in the latest load.
    # ev_operator_pricing and ev_operator_region_analysis are NOT reconciled: the model owner
    # confirmed (14 Oct 2026) that they deliberately filter out some points (13 Oct: pricing
    # 10,862 and region 11,401 of 11,684), so a total-count check would always fail.
    return pd.DataFrame([{
        "diff_raw_rows_vs_staging_rows": len(t["raw"]) - len(t["staging"]),
        "diff_staging_rows_vs_fact_rows": len(t["staging"]) - len(fct),
        "diff_summary_connectors_vs_latest_fact": t["summary"]["total_connectors"].sum() - len(latest),
        # The summary counts available connectors by the point's own status (ev_id_status = 1).
        "diff_summary_available_vs_fact_point_status": (
            t["summary"]["available_connectors"].sum() - (latest["ev_id_status"] == 1).sum()
        ),
    }])


def suite_reconciliation(r):
    # Every column must be exactly 0: between(c, 0, 0) means "min 0 and max 0".
    return [between(c, 0, 0) for c in r.columns]


# ----------------------------------------------------------------------------- running
def run_suite(context, source, name, df, expectations):
    # GX 1.x validates a dataframe through four linked objects:
    #   data source -> data asset -> batch definition -> validation definition (with the suite).
    # The get-or-create pattern below reuses what exists, so the script can run repeatedly.
    try:
        asset = source.get_asset(name)  # reuse the asset if it was created on an earlier run
    except LookupError:
        asset = source.add_dataframe_asset(name=name)
    try:
        batch_def = asset.get_batch_definition(f"{name}_whole")
    except KeyError:
        # "Whole dataframe": validate every row of the dataframe passed at run time.
        batch_def = asset.add_batch_definition_whole_dataframe(f"{name}_whole")
    # add_or_update: create the suite, or overwrite it with the current expectations.
    suite = context.suites.add_or_update(gx.ExpectationSuite(name=f"{name}_suite", expectations=expectations))
    validation = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(name=f"{name}_validation", data=batch_def, suite=suite)
    )
    # The dataframe itself is handed in here, at run time, not stored in the definition.
    return validation.run(batch_parameters={"dataframe": df})


def describe_failures(name, result) -> int:
    # Prints one FAIL line per failed expectation and returns how many failed.
    # (`name` is not used in the body; it is kept for a clearer call site.)
    failed = 0
    for r in result.results:  # one result per expectation
        if r.success:
            continue
        failed += 1
        cfg = r.expectation_config  # which check this was
        # Single-column checks have "column"; compound-key checks have "column_list".
        col = cfg.kwargs.get("column") or cfg.kwargs.get("column_list") or "table"
        res = r.result or {}  # GX's detail: counts and example values
        detail = ""
        if "unexpected_count" in res:
            # Row-level checks: how many rows broke the rule, and a few examples.
            detail = f" - {res['unexpected_count']} unexpected ({res.get('unexpected_percent', 0):.2f}%)"
            sample = res.get("partial_unexpected_list")
            if sample:
                detail += f", e.g. {sample[:3]}"
        elif "observed_value" in res:
            # Table-level checks (such as row count) report one observed value instead.
            detail = f" - observed {res['observed_value']}"
        print(f"  FAIL  {cfg.type}  [{col}]{detail}")
    return failed


def main() -> int:
    # --- 1. Options -----------------------------------------------------------------
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", help="read <key>.csv files from this folder instead of BigQuery")
    args = parser.parse_args()

    try:
        # Optional: loads BQ_PROJECT and similar settings from a .env file if one exists.
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # --- 2. Load and type every table -------------------------------------------------
    raw_tables = load_csv_dir(args.csv_dir) if args.csv_dir else load_bigquery(os.getenv("BQ_PROJECT"))
    t = {k: normalise(v) for k, v in raw_tables.items()}
    print("Rows loaded: " + ", ".join(f"{k}={len(v)}" for k, v in t.items()))

    # --- 3. Derive the flag columns and the reconciliation row ----------------------
    fct = prepare_fct(t["fct"], t["dim"])
    summary = prepare_summary(t["summary"])
    pricing = prepare_price_table(t["pricing"], "charging_points_with_positive_price")
    region = prepare_price_table(t["region"], "points_with_positive_price")
    recon = build_reconciliation(t)
    batches = prepare_history_batches(t["history"])

    # --- 4. The plan: (name, dataframe, expectations) for each table -----------------
    # Adding a table to validate means adding one tuple here.
    plan = [
        ("raw_history", t["history"], suite_layer()),
        ("raw_history_batches", batches, suite_history_batches()),
        ("staging", t["staging"], suite_layer()),
        ("dim_ev_charger", t["dim"], suite_dim(t["dim"])),
        ("fct_ev_charging_points", fct, suite_fct()),
        ("ev_charging_summary", summary, suite_summary(summary)),
        ("ev_operator_pricing", pricing, suite_price_table(["operator"])),
        ("ev_operator_region_analysis", region,
         suite_price_table(["operator", "region"])),
        ("reconciliation", recon, suite_reconciliation(recon)),
    ]

    # --- 5. Run every suite --------------------------------------------------------
    # A "file" context keeps GX's config and results on disk under GX_DIR.
    context = gx.get_context(mode="file", project_root_dir=GX_DIR)
    source = context.data_sources.add_or_update_pandas(name=SOURCE_NAME)

    total = failed = 0
    for name, df, expectations in plan:
        result = run_suite(context, source, name, df, expectations)
        n_fail = sum(1 for r in result.results if not r.success)
        total += len(result.results)
        failed += n_fail
        print(f"{name}: {len(result.results) - n_fail}/{len(result.results)} passed")
        describe_failures(name, result)

    # --- 6. Summary, Data Docs and exit code ---------------------------------------
    print(f"\n{total - failed}/{total} expectations passed across {len(plan)} tables")
    context.build_data_docs()  # writes the HTML report under GX_DIR/gx/uncommitted/data_docs
    sites = context.get_docs_sites_urls()
    if sites:
        print("Data Docs:", sites[0]["site_url"])
    return 1 if failed else 0  # 0 = all passed, 1 = at least one failure


if __name__ == "__main__":
    sys.exit(main())  # hands main()'s return value to the shell as the exit code
