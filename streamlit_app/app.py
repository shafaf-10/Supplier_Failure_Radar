from __future__ import annotations

import os
from datetime import datetime
from html import escape
from typing import Any

import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Page configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Supplier Risk · Afinetrip",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Backend settings
# IMPORTANT:
# Your FastAPI router uses verify_api_key(), so Streamlit MUST send X-API-Key.
# Default API key is taken from app/infra/settings.py: dev-secret-key
# -----------------------------------------------------------------------------
API_BASE_URL = os.getenv("SUPPLIER_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("SUPPLIER_API_KEY", "dev-secret-key")
REQUEST_TIMEOUT = 120

REPORTING_PERIODS = {
    "All Time": "all",
    "Last 24 Hours": "24h",
    "Last 7 Days": "7d",
    "Last 30 Days": "30d",
    "Last 12 Months": "1y",
}

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
html, body, .stApp {
    background: #FAFAFA;
    color: #111111;
    font-family: Arial, sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 2rem 2.5rem 4rem;
    max-width: 100%;
}
section[data-testid="stSidebar"] {
    background: #111111;
    border-right: none;
}
section[data-testid="stSidebar"] * {
    color: #E5E5E5 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stCheckbox label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #AAAAAA !important;
}
.sidebar-logo {
    font-size: 18px;
    font-weight: 700;
    color: #FFFFFF !important;
    padding: 8px 0 2px;
}
.sidebar-cap {
    font-size: 11px;
    color: #888888 !important;
    margin-bottom: 28px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.page-header {
    border-bottom: 1.5px solid #E0E0E0;
    padding-bottom: 18px;
    margin-bottom: 28px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.page-title {
    font-size: 22px;
    font-weight: 700;
    color: #111111;
}
.page-meta {
    font-size: 11px;
    color: #777777;
    text-align: right;
}
.stat-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border: 1.5px solid #E0E0E0;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 26px;
    background: #FFFFFF;
}
.stat-cell {
    padding: 20px 24px;
    border-right: 1.5px solid #E0E0E0;
}
.stat-cell:last-child { border-right: none; }
.stat-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #888888;
    margin-bottom: 6px;
}
.stat-value {
    font-size: 30px;
    font-weight: 700;
    color: #111111;
    line-height: 1;
}
.section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #777777;
    margin-bottom: 12px;
    margin-top: 28px;
}
.alert-card {
    background: #FFFFFF;
    border: 1.5px solid #E0E0E0;
    border-left: 4px solid #111111;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 10px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 12px;
    align-items: start;
}
.alert-supplier {
    font-size: 15px;
    font-weight: 700;
    color: #111111;
    margin-bottom: 3px;
}
.alert-code {
    font-size: 11px;
    color: #888888;
    margin-bottom: 10px;
}
.alert-row {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 12px;
    color: #444444;
}
.alert-row span b {
    color: #111111;
    font-weight: 700;
}
.alert-action {
    font-size: 12px;
    color: #333333;
    margin-top: 8px;
    font-style: italic;
}
.badge {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.b-high { background: #111111; color: #FFFFFF; }
.b-medium { background: #E0E0E0; color: #222222; }
.b-low { background: #F0F0F0; color: #555555; }
.b-warn { background: #111111; color: #FFFFFF; }
.b-watch { background: #E0E0E0; color: #222222; }
.b-stable { background: #F0F0F0; color: #555555; }
.profile-card {
    background: #FFFFFF;
    border: 1.5px solid #E0E0E0;
    border-radius: 8px;
    padding: 24px 28px;
}
.profile-name {
    font-size: 18px;
    font-weight: 700;
    color: #111111;
    margin-bottom: 2px;
}
.profile-code {
    font-size: 11px;
    color: #888888;
    margin-bottom: 20px;
    letter-spacing: 0.04em;
}
.profile-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px 24px;
    margin-bottom: 20px;
}
.pf-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888888;
    margin-bottom: 3px;
}
.pf-value {
    font-size: 15px;
    font-weight: 600;
    color: #111111;
}
.profile-divider {
    border: none;
    border-top: 1.5px solid #E0E0E0;
    margin: 18px 0;
}
.profile-action-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888888;
    margin-bottom: 6px;
}
.profile-action-text {
    font-size: 13px;
    color: #333333;
}
.page-footer {
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1.5px solid #E0E0E0;
    font-size: 10px;
    color: #BBBBBB;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
@media (max-width: 900px) {
    .stat-row { grid-template-columns: repeat(2, 1fr); }
    .profile-grid { grid-template-columns: repeat(1, 1fr); }
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def to_num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def fmt_pct(value: Any) -> str:
    number = to_num(value)
    if number > 1:
        return f"{number:.1f}%"
    if number >= 0.995:
        return "99.9%+"
    if 0 < number <= 0.005:
        return "<0.5%"
    return f"{number * 100:.1f}%"


def clean_text(text: Any) -> str:
    value = str(text or "Continue monitoring.")
    value = value.replace("(100.0%)", "(99.9%+)").replace("(0.0%)", "(<0.5%)")
    return escape(value)


def supplier_name(row: pd.Series) -> str:
    return str(row.get("supplier_name") or row.get("supplier_code") or "Unknown")


def normalize_risk_level(value: Any) -> str:
    value = str(value or "LOW_RISK").upper().strip()
    mapping = {
        "HIGH": "HIGH_RISK",
        "MEDIUM": "MEDIUM_RISK",
        "LOW": "LOW_RISK",
    }
    return mapping.get(value, value)


def normalize_warning_status(value: Any) -> str:
    value = str(value or "STABLE").upper().strip()
    mapping = {
        "CRITICAL": "CRITICAL_WARNING",
        "NORMAL": "STABLE",
    }
    return mapping.get(value, value)


def risk_badge(level: Any) -> str:
    level = normalize_risk_level(level)
    if level == "HIGH_RISK":
        return '<span class="badge b-high">High</span>'
    if level == "MEDIUM_RISK":
        return '<span class="badge b-medium">Medium</span>'
    return '<span class="badge b-low">Low</span>'


def warning_badge(status: Any) -> str:
    status = normalize_warning_status(status)
    if status == "CRITICAL_WARNING":
        return '<span class="badge b-warn">Critical</span>'
    if status == "WARNING":
        return '<span class="badge b-warn">Warning</span>'
    if status == "WATCHLIST":
        return '<span class="badge b-watch">Watchlist</span>'
    return '<span class="badge b-stable">Stable</span>'


def show_api_error(error: Exception) -> None:
    st.error(f"Cannot load supplier prediction data: {error}")

    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response
        status_code = response.status_code if response is not None else "unknown"
        detail = ""
        try:
            detail = response.json().get("detail", "") if response is not None else ""
        except Exception:
            detail = response.text if response is not None else ""

        st.warning(f"Backend returned HTTP {status_code}. {detail}")

        if status_code == 401:
            st.info(
                "Your FastAPI backend requires X-API-Key. This corrected Streamlit code sends it. "
                "Check that SUPPLIER_API_KEY matches API_KEY in .env or app/infra/settings.py."
            )

    st.code(
        "# Terminal 1\n"
        "python -m uvicorn app.main:app --reload --port 8000\n\n"
        "# Terminal 2\n"
        "python -m streamlit run streamlit_app/app.py",
        language="bash",
    )


# -----------------------------------------------------------------------------
# API functions
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def fetch_supplier_data(period: str) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}/supplier-predictions",
        params={"period": period, "limit": 100, "offset": 0},
        headers=api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def refresh_backend() -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/refresh-model",
        headers=api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-logo">Afinetrip</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-cap">Supplier Risk</div>', unsafe_allow_html=True)

    reporting_period_label = st.selectbox("Period", list(REPORTING_PERIODS.keys()))
    risk_filter = st.selectbox("Risk Level", ["All", "HIGH_RISK", "MEDIUM_RISK", "LOW_RISK"])
    warning_filter = st.selectbox(
        "Status",
        ["All", "CRITICAL_WARNING", "WARNING", "WATCHLIST", "STABLE"],
    )
    anomaly_only = st.checkbox("Anomalies only")
    supplier_search = st.text_input("Search", placeholder="Name or code")

    st.divider()
    st.caption(f"API: {API_BASE_URL}")

    col_a, col_b = st.columns(2)
    with col_a:
        soft_refresh = st.button("Reload", use_container_width=True)
    with col_b:
        hard_refresh = st.button("Run API", use_container_width=True)

    if soft_refresh:
        st.cache_data.clear()
        st.rerun()

    if hard_refresh:
        with st.spinner("Running supplier pipeline..."):
            try:
                refresh_backend()
                st.cache_data.clear()
                st.success("Pipeline refreshed.")
                st.rerun()
            except Exception as exc:
                show_api_error(exc)
                st.stop()

# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
period = REPORTING_PERIODS[reporting_period_label]

try:
    with st.spinner("Loading supplier predictions..."):
        data = fetch_supplier_data(period)
except Exception as exc:
    show_api_error(exc)
    st.stop()

summary = data.get("summary", {}) or {}
df = pd.DataFrame(data.get("suppliers", []) or [])

if df.empty:
    st.warning("No supplier prediction records found.")
    st.stop()

# -----------------------------------------------------------------------------
# Safe default columns
# -----------------------------------------------------------------------------
DEFAULTS = {
    "supplier_code": "",
    "supplier_name": "",
    "risk_score": 0,
    "risk_level": "LOW_RISK",
    "predicted_risk": "LOW_RISK",
    "prediction_probability": 0,
    "anomaly_status": "NORMAL",
    "anomaly_score": 0,
    "recommendation": "Continue monitoring.",
    "future_instability_probability": 0,
    "future_instability_percentage": None,
    "future_risk_window": "N/A",
    "early_warning_status": "STABLE",
    "lead_signal": "N/A",
    "prediction_confidence": "N/A",
    "future_recommendation": "Continue monitoring.",
    "total_bookings": 0,
    "failure_rate": 0,
    "pending_rate": 0,
    "cancellation_rate": 0,
    "process_error_rate": 0,
    "refund_rate": 0,
    "credit_rejection_rate": 0,
    "search_failure_rate": 0,
    "wallet_risk_rate": 0,
}

for column_name, default_value in DEFAULTS.items():
    if column_name not in df.columns:
        df[column_name] = default_value

# Normalize values from backend
df["risk_level"] = df["risk_level"].apply(normalize_risk_level)
df["early_warning_status"] = df["early_warning_status"].apply(normalize_warning_status)
df["anomaly_status"] = df["anomaly_status"].astype(str).str.upper().fillna("NORMAL")

for numeric_column in [
    "risk_score",
    "prediction_probability",
    "future_instability_probability",
    "future_instability_percentage",
    "total_bookings",
    "failure_rate",
    "pending_rate",
    "cancellation_rate",
    "process_error_rate",
    "refund_rate",
    "credit_rejection_rate",
    "search_failure_rate",
    "wallet_risk_rate",
    "anomaly_score",
]:
    df[numeric_column] = pd.to_numeric(df[numeric_column], errors="coerce").fillna(0)

# Use percentage column if backend sends it, otherwise use probability 0 to 1.
df["_future_prob"] = df.apply(
    lambda row: (
        to_num(row.get("future_instability_percentage")) / 100
        if to_num(row.get("future_instability_percentage")) > 0
        else to_num(row.get("future_instability_probability"))
    ),
    axis=1,
)

# -----------------------------------------------------------------------------
# Filters
# -----------------------------------------------------------------------------
filtered = df.copy()

if risk_filter != "All":
    filtered = filtered[filtered["risk_level"] == risk_filter]

if warning_filter != "All":
    filtered = filtered[filtered["early_warning_status"] == warning_filter]

if anomaly_only:
    filtered = filtered[filtered["anomaly_status"] == "ANOMALY"]

if supplier_search:
    search_text = supplier_search.strip()
    mask = (
        filtered["supplier_code"].astype(str).str.contains(search_text, case=False, na=False)
        | filtered["supplier_name"].astype(str).str.contains(search_text, case=False, na=False)
    )
    filtered = filtered[mask]

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown(
    f"""
<div class="page-header">
    <div>
        <div class="page-title">Supplier Risk Overview</div>
        <div style="font-size:12px;color:#777;margin-top:4px;">FastAPI + ML supplier failure monitoring</div>
    </div>
    <div class="page-meta">
        {datetime.now().strftime("%d %b %Y · %H:%M")}<br>
        {escape(reporting_period_label)}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Summary cards
# -----------------------------------------------------------------------------
total_suppliers = summary.get("total_suppliers", len(df))
high_risk_suppliers = summary.get(
    "high_risk_suppliers", int((df["risk_level"] == "HIGH_RISK").sum())
)
anomaly_suppliers = summary.get(
    "anomaly_suppliers", int((df["anomaly_status"] == "ANOMALY").sum())
)
critical_future_warnings = summary.get(
    "critical_future_warnings",
    int((df["early_warning_status"] == "CRITICAL_WARNING").sum()),
)

st.markdown(
    f"""
<div class="stat-row">
    <div class="stat-cell">
        <div class="stat-label">Suppliers</div>
        <div class="stat-value">{to_int(total_suppliers)}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">Critical</div>
        <div class="stat-value">{to_int(critical_future_warnings)}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">High Risk</div>
        <div class="stat-value">{to_int(high_risk_suppliers)}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">Anomalies</div>
        <div class="stat-value">{to_int(anomaly_suppliers)}</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Immediate action cards
# -----------------------------------------------------------------------------
st.markdown('<div class="section-label">Requires Immediate Action</div>', unsafe_allow_html=True)

critical_df = filtered[filtered["early_warning_status"] == "CRITICAL_WARNING"].sort_values(
    "_future_prob", ascending=False
)

if critical_df.empty:
    st.success("No suppliers require immediate action for the selected filters.")
else:
    for _, row in critical_df.head(5).iterrows():
        st.markdown(
            f"""
<div class="alert-card">
    <div>
        <div class="alert-supplier">{escape(supplier_name(row))}</div>
        <div class="alert-code">{escape(str(row.get("supplier_code")))}</div>
        <div class="alert-row">
            <span><b>Future Risk</b> {fmt_pct(row.get("_future_prob"))}</span>
            <span><b>Level</b> {risk_badge(row.get("risk_level"))}</span>
            <span><b>Window</b> {escape(str(row.get("future_risk_window") or "N/A"))}</span>
            <span><b>Bookings</b> {to_int(row.get("total_bookings"))}</span>
            <span><b>Failure Rate</b> {fmt_pct(row.get("failure_rate"))}</span>
        </div>
        <div class="alert-action">{clean_text(row.get("future_recommendation") or row.get("recommendation"))}</div>
    </div>
    <div>{warning_badge(row.get("early_warning_status"))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# Supplier table
# -----------------------------------------------------------------------------
st.markdown('<div class="section-label">All Suppliers</div>', unsafe_allow_html=True)

if filtered.empty:
    st.info("No records match the selected filters.")
else:
    table_df = filtered.copy()
    table_df["Supplier"] = table_df.apply(
        lambda row: f"{supplier_name(row)} · {row.get('supplier_code')}", axis=1
    )
    table_df["Risk Level"] = table_df["risk_level"].replace(
        {"HIGH_RISK": "High", "MEDIUM_RISK": "Medium", "LOW_RISK": "Low"}
    )
    table_df["Future Risk"] = table_df["_future_prob"].apply(fmt_pct)
    table_df["Status"] = table_df["early_warning_status"].replace(
        {
            "CRITICAL_WARNING": "Critical",
            "WARNING": "Warning",
            "WATCHLIST": "Watchlist",
            "STABLE": "Stable",
        }
    )
    table_df["Failure Rate"] = table_df["failure_rate"].apply(fmt_pct)
    table_df["Pending Rate"] = table_df["pending_rate"].apply(fmt_pct)
    table_df["Bookings"] = table_df["total_bookings"].apply(to_int)
    table_df["Risk Score"] = table_df["risk_score"].round(2)
    table_df["Anomaly"] = table_df["anomaly_status"]

    display_columns = [
        "Supplier",
        "Risk Level",
        "Risk Score",
        "Future Risk",
        "Status",
        "Failure Rate",
        "Pending Rate",
        "Bookings",
        "Anomaly",
    ]

    st.dataframe(
        table_df.sort_values("risk_score", ascending=False)[display_columns],
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------------------------------------------------------
# Supplier detail
# -----------------------------------------------------------------------------
st.markdown('<div class="section-label">Supplier Detail</div>', unsafe_allow_html=True)

if not filtered.empty:
    options_df = filtered.sort_values("risk_score", ascending=False).copy()
    options_df["_option"] = options_df.apply(
        lambda row: f"{supplier_name(row)} — {row.get('supplier_code')}", axis=1
    )

    selected_option = st.selectbox(
        "Select supplier",
        options_df["_option"].tolist(),
        label_visibility="collapsed",
    )
    selected_code = selected_option.split("—")[-1].strip()
    selected_rows = filtered[filtered["supplier_code"].astype(str) == selected_code]

    if not selected_rows.empty:
        row = selected_rows.iloc[0]
        recommendation_text = row.get("future_recommendation") or row.get("recommendation")

        st.markdown(
            f"""
<div class="profile-card">
    <div class="profile-name">{escape(supplier_name(row))}</div>
    <div class="profile-code">{escape(str(row.get("supplier_code")))}</div>
    <div class="profile-grid">
        <div class="profile-field">
            <div class="pf-label">Risk Level</div>
            <div class="pf-value">{risk_badge(row.get("risk_level"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Risk Score</div>
            <div class="pf-value">{to_num(row.get("risk_score")):.2f}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Future Probability</div>
            <div class="pf-value">{fmt_pct(row.get("_future_prob"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Status</div>
            <div class="pf-value">{warning_badge(row.get("early_warning_status"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Future Window</div>
            <div class="pf-value">{escape(str(row.get("future_risk_window") or "N/A"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Confidence</div>
            <div class="pf-value">{escape(str(row.get("prediction_confidence") or "N/A"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Total Bookings</div>
            <div class="pf-value">{to_int(row.get("total_bookings"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Failure Rate</div>
            <div class="pf-value">{fmt_pct(row.get("failure_rate"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Pending Rate</div>
            <div class="pf-value">{fmt_pct(row.get("pending_rate"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Process Error Rate</div>
            <div class="pf-value">{fmt_pct(row.get("process_error_rate"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Search Failure Rate</div>
            <div class="pf-value">{fmt_pct(row.get("search_failure_rate"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Wallet Risk Rate</div>
            <div class="pf-value">{fmt_pct(row.get("wallet_risk_rate"))}</div>
        </div>
    </div>
    <hr class="profile-divider">
    <div class="profile-action-label">Lead Signal</div>
    <div class="profile-action-text">{escape(str(row.get("lead_signal") or "N/A"))}</div>
    <br>
    <div class="profile-action-label">Recommended Action</div>
    <div class="profile-action-text">{clean_text(recommendation_text)}</div>
</div>
""",
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# Filtered CSV download
# -----------------------------------------------------------------------------
csv_data = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered CSV",
    data=csv_data,
    file_name=f"supplier_predictions_{period}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown(
    f"""
<div class="page-footer">
    Afinetrip Pvt. Ltd. · Internal Use Only · Refreshed {datetime.now().strftime("%d %b %Y %H:%M")}
</div>
""",
    unsafe_allow_html=True,
)