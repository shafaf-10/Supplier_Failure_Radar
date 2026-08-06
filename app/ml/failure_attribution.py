"""
Failure attribution.

Classifies every failure row in search_sessions, booking_processes, and
bookings as SUPPLIER, INTERNAL, TIMEOUT, or UNKNOWN, so supplier risk
scoring, ML features, and supplier alerts only reflect failures actually
caused by suppliers -- not bugs in our own platform code.

Precedence (first match wins), per row:
    1. Structured failure_source column, if present and valid (Laravel tag).
    2. Row falls inside a detected platform-incident window -> INTERNAL.
    3. Keyword classification on the row's free-text error field.
    4. (search_sessions only) Search-isolation via criteria_hash.
    5. Else UNKNOWN.

See README.md "Failure Attribution (Laravel <-> Radar contract)" for the
full contract this module implements.
"""

import pandas as pd

from app.infra.settings import settings
from app.observability.logger import setup_logger

logger = setup_logger(__name__)

SUPPLIER_SOURCES = {"SUPPLIER", "TIMEOUT", "UNKNOWN"}
_VALID_SOURCES = SUPPLIER_SOURCES | {"INTERNAL"}

INTERNAL_KEYWORDS = [
    "timeout",
    "timed out",
    "500",
    "internal server",
    "exception",
    "unhandled",
    "laravel",
    "query exception",
    "sqlstate",
    "redis",
    "queue",
    "undefined",
    "attempt to read property",
]

SUPPLIER_KEYWORDS = [
    "no availability",
    "invalid pnr",
    "supplier down",
    "upstream",
    "fare quote",
    "airline",
    "gds",
    "third party",
]

# Per-table shape: which column marks a row failed, which values count as a
# failure, which column(s) hold free text for keyword classification, which
# column identifies the supplier, and which column is the event date.
_TABLE_CONFIG = {
    "search_sessions": {
        "status_col": "status",
        "failed_values": {"FAILED", "TIMEOUT", "PARTIAL"},
        "text_cols": ["error_context", "warnings"],
        "supplier_col": "supplier_code",
        "date_col": "created_at",
    },
    "booking_processes": {
        "status_col": "state",
        "failed_values": {"FAILED", "ERROR", "CANCELLED", "CANCELED"},
        "text_cols": ["error_context", "warnings"],
        "supplier_col": "provider_code",
        "date_col": "created_at",
    },
    "bookings": {
        "status_col": "status",
        "failed_values": {"FAILED", "EXPIRED", "CANCELLED", "CANCELED"},
        "text_cols": ["warnings", "error_context"],
        "supplier_col": "provider",
        "date_col": "booking_date",
    },
}


def _is_failed_row(df: pd.DataFrame, cfg: dict) -> pd.Series:
    status_col = cfg["status_col"]
    if status_col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    return df[status_col].astype(str).str.upper().isin(cfg["failed_values"])


def _classify_by_keywords(text) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    lowered = text.lower()
    has_supplier = any(kw in lowered for kw in SUPPLIER_KEYWORDS)
    has_internal = any(kw in lowered for kw in INTERNAL_KEYWORDS)
    if has_supplier:
        return "SUPPLIER"
    if has_internal:
        return "INTERNAL"
    return None


def _combined_text(row: pd.Series, text_cols: list) -> str:
    parts = [str(row[c]) for c in text_cols if c in row.index and pd.notna(row[c])]
    return " ".join(parts)


def detect_platform_incident_windows(frames: dict) -> tuple[list, dict]:
    """
    Looks across all three tables for days where the failure rate spikes far
    above baseline AND most active suppliers are affected at once -- the
    signature of a platform-wide bug rather than one supplier's problem.

    Returns (incident_day_windows_as_strings, summary_dict). summary_dict
    includes whether the most recent day in the data is an active incident.
    """
    incident_days: set = set()
    latest_day = None

    for table_name, cfg in _TABLE_CONFIG.items():
        df = frames.get(table_name)
        if df is None or df.empty:
            continue

        date_col, supplier_col = cfg["date_col"], cfg["supplier_col"]
        if date_col not in df.columns or supplier_col not in df.columns:
            continue

        work = df.copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.dropna(subset=[date_col])
        if work.empty:
            continue

        work["_day"] = work[date_col].dt.date
        work["_failed"] = _is_failed_row(work, cfg)

        table_latest = work["_day"].max()
        if latest_day is None or table_latest > latest_day:
            latest_day = table_latest

        daily = work.groupby("_day").agg(
            total=(supplier_col, "count"),
            failed=("_failed", "sum"),
        )
        daily["failed_rate"] = daily["failed"] / daily["total"].replace(0, 1)

        affected_suppliers = (
            work[work["_failed"]].groupby("_day")[supplier_col].nunique()
        )
        active_suppliers = work.groupby("_day")[supplier_col].nunique()

        for day, row in daily.iterrows():
            baseline_window = daily[daily.index < day].tail(
                settings.INCIDENT_BASELINE_DAYS
            )
            if baseline_window.empty:
                continue

            baseline = baseline_window["failed_rate"].median()
            threshold = max(
                baseline * settings.INCIDENT_RATE_MULTIPLIER,
                baseline + settings.INCIDENT_MIN_ABS_RATE_DELTA,
            )

            active_count = active_suppliers.get(day, 0)
            affected_fraction = (
                affected_suppliers.get(day, 0) / active_count if active_count else 0
            )

            if (
                row["failed_rate"] > threshold
                and affected_fraction >= settings.INCIDENT_MIN_AFFECTED_FRACTION
                and row["total"] >= settings.INCIDENT_MIN_EVENTS
            ):
                incident_days.add(day)

    windows = sorted(str(day) for day in incident_days)
    active_now = latest_day is not None and latest_day in incident_days

    if windows:
        logger.warning("Platform incident window(s) detected: %s", windows)

    summary = {"platform_incident": active_now, "incident_windows": windows}
    return windows, summary


def classify_search_isolation(sessions: pd.DataFrame) -> pd.DataFrame:
    """
    Groups search_sessions rows by (criteria_hash, day). If every supplier
    queried for that search failed, the search itself broke (INTERNAL). If
    only some suppliers failed, those specific suppliers are the problem
    (SUPPLIER). Only fills rows that don't already have a failure_source.
    """
    if sessions is None or sessions.empty:
        return sessions

    cfg = _TABLE_CONFIG["search_sessions"]
    date_col = cfg["date_col"]
    if "criteria_hash" not in sessions.columns or date_col not in sessions.columns:
        return sessions

    work = sessions.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work["_day"] = work[date_col].dt.date
    work["_failed"] = _is_failed_row(work, cfg)

    group_all_failed = work.groupby(["criteria_hash", "_day"])["_failed"].transform(
        "all"
    )

    if "failure_source" in work.columns:
        resolved = work["failure_source"].copy()
    else:
        resolved = pd.Series([None] * len(work), index=work.index, dtype=object)

    unresolved = resolved.isna() & work["_failed"]
    resolved.loc[unresolved & group_all_failed] = "INTERNAL"
    resolved.loc[unresolved & ~group_all_failed] = "SUPPLIER"

    sessions = sessions.copy()
    sessions["failure_source"] = resolved
    return sessions


def attribute_failure_sources(frames: dict) -> dict:
    """
    Adds/completes the failure_source column on search_sessions,
    booking_processes, and bookings. Only failed rows are classified;
    successful rows are left alone and always survive filtering.
    """
    frames = dict(frames)

    _, incident_summary = detect_platform_incident_windows(frames)
    incident_days = {
        pd.to_datetime(day).date() for day in incident_summary["incident_windows"]
    }

    for table_name, cfg in _TABLE_CONFIG.items():
        df = frames.get(table_name)
        if df is None or df.empty:
            continue

        df = df.copy()
        is_failed = _is_failed_row(df, cfg)

        if "failure_source" in df.columns:
            structured = df["failure_source"].astype(str).str.upper()
            has_valid_tag = structured.isin(_VALID_SOURCES)
        else:
            structured = pd.Series([None] * len(df), index=df.index)
            has_valid_tag = pd.Series([False] * len(df), index=df.index)

        resolved = pd.Series([None] * len(df), index=df.index, dtype=object)
        resolved.loc[has_valid_tag] = structured.loc[has_valid_tag]

        # Step 2: platform-incident window -> INTERNAL
        if cfg["date_col"] in df.columns and incident_days:
            day = pd.to_datetime(df[cfg["date_col"]], errors="coerce").dt.date
            in_incident = day.isin(incident_days)
            unresolved = resolved.isna() & is_failed
            resolved.loc[unresolved & in_incident] = "INTERNAL"

        # Step 3: keyword classification
        unresolved = resolved.isna() & is_failed
        text_cols = [c for c in cfg["text_cols"] if c in df.columns]
        if unresolved.any() and text_cols:
            texts = df.loc[unresolved, text_cols].apply(
                lambda row: _combined_text(row, text_cols), axis=1
            )
            resolved.loc[unresolved] = texts.apply(_classify_by_keywords)

        df["failure_source"] = resolved
        frames[table_name] = df

    # Step 4: search-session isolation (search_sessions only)
    if "search_sessions" in frames:
        frames["search_sessions"] = classify_search_isolation(
            frames["search_sessions"]
        )

    # Step 5: anything still unresolved among failed rows -> UNKNOWN
    for table_name, cfg in _TABLE_CONFIG.items():
        df = frames.get(table_name)
        if df is None or df.empty or "failure_source" not in df.columns:
            continue
        is_failed = _is_failed_row(df, cfg)
        still_unresolved = df["failure_source"].isna() & is_failed
        df.loc[still_unresolved, "failure_source"] = "UNKNOWN"
        frames[table_name] = df

    return frames


def filter_supplier_sources(df: pd.DataFrame) -> pd.DataFrame:
    """Drops INTERNAL-attributed rows; leaves everything else (including
    non-failure rows, which never get a failure_source) untouched."""
    if df is None or df.empty or "failure_source" not in df.columns:
        return df
    return df[df["failure_source"] != "INTERNAL"].copy()


def compute_internal_failure_counts(frames: dict) -> pd.DataFrame:
    """Per-supplier count and rate of INTERNAL-attributed failures, purely
    for dashboard visibility -- these never count against supplier risk."""
    totals: dict = {}
    internal_counts: dict = {}

    for table_name, cfg in _TABLE_CONFIG.items():
        df = frames.get(table_name)
        supplier_col = cfg["supplier_col"]
        if df is None or df.empty or supplier_col not in df.columns:
            continue

        for supplier_code, count in df.groupby(supplier_col).size().items():
            totals[supplier_code] = totals.get(supplier_code, 0) + count

        if "failure_source" not in df.columns:
            continue

        internal = df[df["failure_source"] == "INTERNAL"]
        for supplier_code, count in internal.groupby(supplier_col).size().items():
            internal_counts[supplier_code] = (
                internal_counts.get(supplier_code, 0) + count
            )

    suppliers = sorted(set(totals) | set(internal_counts))
    result = pd.DataFrame(
        {
            "supplier_code": suppliers,
            "internal_failure_count": [internal_counts.get(s, 0) for s in suppliers],
        }
    )
    result["internal_failure_rate"] = [
        (internal_counts.get(s, 0) / totals[s]) if totals.get(s) else 0.0
        for s in suppliers
    ]
    return result