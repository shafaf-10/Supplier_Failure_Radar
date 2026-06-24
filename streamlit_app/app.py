from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Supplier Risk · Afinetrip",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://127.0.0.1:8000"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, .stApp {
    background: #FAFAFA;
    color: #111111;
    font-family: 'Inter', sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 2rem 2.5rem 4rem;
    max-width: 100%;
}

/* ── Sidebar ── */
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
    color: #888888 !important;
}
section[data-testid="stSidebar"] .sidebar-logo {
    font-size: 17px;
    font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: -0.02em;
    padding: 8px 0 2px;
}
section[data-testid="stSidebar"] .sidebar-cap {
    font-size: 11px;
    color: #666666 !important;
    margin-bottom: 28px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── Page header ── */
.page-header {
    border-bottom: 1.5px solid #E0E0E0;
    padding-bottom: 18px;
    margin-bottom: 28px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.page-title {
    font-size: 20px;
    font-weight: 700;
    color: #111111;
    letter-spacing: -0.02em;
}
.page-meta {
    font-size: 11px;
    color: #888888;
    text-align: right;
    letter-spacing: 0.03em;
}

/* ── Stat strip ── */
.stat-row {
    display: flex;
    gap: 0;
    border: 1.5px solid #E0E0E0;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 32px;
    background: #FFFFFF;
}
.stat-cell {
    flex: 1;
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
    letter-spacing: -0.03em;
    line-height: 1;
}
.stat-value.alert { color: #111111; }

/* ── Section label ── */
.section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #888888;
    margin-bottom: 12px;
    margin-top: 32px;
}

/* ── Alert cards ── */
.alert-card {
    background: #FFFFFF;
    border: 1.5px solid #E0E0E0;
    border-left: 3px solid #111111;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 10px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 12px;
    align-items: start;
}
.alert-supplier {
    font-size: 14px;
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
    font-weight: 600;
}
.alert-action {
    font-size: 11px;
    color: #444444;
    margin-top: 8px;
    font-style: italic;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.b-high    { background: #111111; color: #FFFFFF; }
.b-medium  { background: #E0E0E0; color: #333333; }
.b-low     { background: #F0F0F0; color: #666666; }
.b-warn    { background: #111111; color: #FFFFFF; }
.b-watch   { background: #E0E0E0; color: #333333; }
.b-stable  { background: #F0F0F0; color: #666666; }

/* ── Profile card ── */
.profile-card {
    background: #FFFFFF;
    border: 1.5px solid #E0E0E0;
    border-radius: 8px;
    padding: 24px 28px;
}
.profile-name {
    font-size: 17px;
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
.profile-field { }
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

/* ── Footer ── */
.page-footer {
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1.5px solid #E0E0E0;
    font-size: 10px;
    color: #BBBBBB;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
</style>
""",
    unsafe_allow_html=True,
)


REPORTING_PERIODS = {
    "All Time": "all",
    "Last 24 Hours": "24h",
    "Last 7 Days": "7d",
    "Last 30 Days": "30d",
    "Last 12 Months": "1y",
}


def to_num(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except Exception:
        return default


def fmt_pct(value):
    value = to_num(value)
    if value > 1:
        return f"{value:.1f}%"
    if value >= 0.995:
        return "99.9%+"
    if 0 < value <= 0.005:
        return "<0.5%"
    return f"{value * 100:.1f}%"


def clean_text(text):
    text = str(text or "Continue monitoring.")
    text = text.replace("(100.0%)", "(99.9%+)").replace("(0.0%)", "(<0.5%)")
    return text


def supplier_name(row):
    return str(row.get("supplier_name") or row.get("supplier_code") or "Unknown")


def risk_badge(level):
    level = str(level or "").upper()
    if level == "HIGH_RISK":
        return '<span class="badge b-high">High</span>'
    if level == "MEDIUM_RISK":
        return '<span class="badge b-medium">Medium</span>'
    return '<span class="badge b-low">Low</span>'


def warning_badge(status):
    status = str(status or "").upper()
    if status == "CRITICAL_WARNING":
        return '<span class="badge b-warn">Critical</span>'
    if status in ("WARNING",):
        return '<span class="badge b-warn">Warning</span>'
    if status == "WATCHLIST":
        return '<span class="badge b-watch">Watchlist</span>'
    return '<span class="badge b-stable">Stable</span>'


@st.cache_data(ttl=30)
def fetch_supplier_data(period):
    response = requests.get(
        f"{API_URL}/supplier-predictions",
        params={"period": period},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">Afinetrip</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-cap">Supplier Risk</div>', unsafe_allow_html=True)

    reporting_period = st.selectbox("Period", list(REPORTING_PERIODS.keys()))
    risk_filter = st.selectbox("Risk Level", ["All", "HIGH_RISK", "MEDIUM_RISK", "LOW_RISK"])
    warning_filter = st.selectbox("Status", ["All", "CRITICAL_WARNING", "WARNING", "WATCHLIST", "STABLE"])
    anomaly_only = st.checkbox("Anomalies only")
    supplier_search = st.text_input("Search", placeholder="Name or code")

    st.divider()
    if st.button("↻  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Fetch data ────────────────────────────────────────────────────────────────
try:
    data = fetch_supplier_data(REPORTING_PERIODS[reporting_period])
except Exception as error:
    st.error(f"Cannot reach backend: {error}")
    st.info("Start the API: uvicorn app.main:app --reload --port 8000")
    st.stop()

summary = data.get("summary", {})
df = pd.DataFrame(data.get("suppliers", []))

if df.empty:
    st.warning("No records found.")
    st.stop()

DEFAULTS = {
    "supplier_code": "", "supplier_name": "", "risk_score": 0,
    "risk_level": "LOW_RISK", "predicted_risk": "LOW_RISK",
    "prediction_probability": 0, "future_instability_probability": 0,
    "future_instability_percentage": None, "early_warning_status": "STABLE",
    "future_recommendation": "Continue monitoring.", "anomaly_status": "NORMAL",
    "anomaly_score": 0, "total_bookings": 0, "failure_rate": 0,
    "pending_rate": 0, "process_error_rate": 0,
    "search_failure_rate": 0, "wallet_risk_rate": 0,
}
for col, default in DEFAULTS.items():
    if col not in df.columns:
        df[col] = default

df["_prob"] = df.apply(
    lambda r: (
        r["future_instability_percentage"] / 100
        if pd.notna(r.get("future_instability_percentage"))
        else r["future_instability_probability"]
    ),
    axis=1,
)

# ── Filters ───────────────────────────────────────────────────────────────────
filtered = df.copy()
if risk_filter != "All":
    filtered = filtered[filtered["risk_level"] == risk_filter]
if warning_filter != "All":
    filtered = filtered[filtered["early_warning_status"] == warning_filter]
if anomaly_only:
    filtered = filtered[filtered["anomaly_status"] == "ANOMALY"]
if supplier_search:
    mask = (
        filtered["supplier_code"].astype(str).str.contains(supplier_search, case=False, na=False)
        | filtered["supplier_name"].astype(str).str.contains(supplier_search, case=False, na=False)
    )
    filtered = filtered[mask]


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="page-header">
    <div class="page-title">Supplier Risk Overview</div>
    <div class="page-meta">
        {datetime.now().strftime("%d %b %Y · %H:%M")}<br>
        {reporting_period}
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ── Summary strip ─────────────────────────────────────────────────────────────
total = summary.get("total_suppliers", len(df))
critical = summary.get("critical_future_warnings", 0)
high_risk = summary.get("high_risk_suppliers", 0)
anomalies = summary.get("anomaly_suppliers", 0)

st.markdown(
    f"""
<div class="stat-row">
    <div class="stat-cell">
        <div class="stat-label">Suppliers</div>
        <div class="stat-value">{total}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">Critical</div>
        <div class="stat-value alert">{critical}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">High Risk</div>
        <div class="stat-value">{high_risk}</div>
    </div>
    <div class="stat-cell">
        <div class="stat-label">Anomalies</div>
        <div class="stat-value">{anomalies}</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ── Immediate attention ────────────────────────────────────────────────────────
critical_df = filtered[filtered["early_warning_status"] == "CRITICAL_WARNING"].sort_values(
    "_prob", ascending=False
)

st.markdown('<div class="section-label">Requires Immediate Action</div>', unsafe_allow_html=True)

if critical_df.empty:
    st.success("No suppliers require immediate action.")
else:
    for _, row in critical_df.head(5).iterrows():
        st.markdown(
            f"""
<div class="alert-card">
    <div>
        <div class="alert-supplier">{supplier_name(row)}</div>
        <div class="alert-code">{row.get("supplier_code")}</div>
        <div class="alert-row">
            <span><b>Risk</b> {fmt_pct(row.get("_prob"))}</span>
            <span><b>Level</b> {risk_badge(row.get("risk_level"))}</span>
            <span><b>Bookings</b> {int(to_num(row.get("total_bookings")))}</span>
            <span><b>Failure Rate</b> {fmt_pct(row.get("failure_rate"))}</span>
        </div>
        <div class="alert-action">{clean_text(row.get("future_recommendation"))}</div>
    </div>
    <div>{warning_badge(row.get("early_warning_status"))}</div>
</div>
""",
            unsafe_allow_html=True,
        )


# ── Supplier table ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">All Suppliers</div>', unsafe_allow_html=True)

if filtered.empty:
    st.info("No records match current filters.")
else:
    reg = filtered.copy()
    reg["Supplier"] = reg.apply(
        lambda r: f"{supplier_name(r)} · {r.get('supplier_code')}", axis=1
    )
    reg["Risk Level"] = reg["risk_level"].map(
        {"HIGH_RISK": "High", "MEDIUM_RISK": "Medium", "LOW_RISK": "Low"}
    )
    reg["Risk %"] = reg["_prob"].apply(fmt_pct)
    reg["Status"] = reg["early_warning_status"].map(
        {"CRITICAL_WARNING": "Critical", "WARNING": "Warning", "WATCHLIST": "Watchlist", "STABLE": "Stable"}
    )
    reg["Failure Rate"] = reg["failure_rate"].apply(fmt_pct)
    reg["Bookings"] = reg["total_bookings"].apply(lambda x: int(to_num(x)))

    table = (
        reg[["Supplier", "Risk Level", "Risk %", "Status", "Failure Rate", "Bookings", "_prob"]]
        .sort_values("_prob", ascending=False)
        .drop(columns=["_prob"])
    )

    st.dataframe(table, use_container_width=True, hide_index=True)


# ── Supplier profile ───────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Supplier Detail</div>', unsafe_allow_html=True)

if not filtered.empty:
    options = (
        filtered.sort_values("_prob", ascending=False)
        .apply(lambda r: f"{supplier_name(r)} — {r.get('supplier_code')}", axis=1)
        .tolist()
    )
    selected = st.selectbox("Select supplier", options, label_visibility="collapsed")
    selected_code = selected.split("—")[-1].strip()
    row = filtered[filtered["supplier_code"].astype(str) == selected_code].iloc[0]

    st.markdown(
        f"""
<div class="profile-card">
    <div class="profile-name">{supplier_name(row)}</div>
    <div class="profile-code">{row.get("supplier_code")}</div>
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
            <div class="pf-label">Risk Probability</div>
            <div class="pf-value">{fmt_pct(row.get("_prob"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Status</div>
            <div class="pf-value">{warning_badge(row.get("early_warning_status"))}</div>
        </div>
        <div class="profile-field">
            <div class="pf-label">Total Bookings</div>
            <div class="pf-value">{int(to_num(row.get("total_bookings")))}</div>
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
            <div class="pf-label">Wallet Risk Rate</div>
            <div class="pf-value">{fmt_pct(row.get("wallet_risk_rate"))}</div>
        </div>
    </div>
    <hr class="profile-divider">
    <div class="profile-action-label">Recommended Action</div>
    <div class="profile-action-text">{clean_text(row.get("future_recommendation"))}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="page-footer">
    Afinetrip Pvt. Ltd. · Internal Use Only · Refreshed {datetime.now().strftime("%d %b %Y %H:%M")}
</div>
""",
    unsafe_allow_html=True,
)