from datetime import datetime

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Supplier Risk Management · Afinetrip",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://127.0.0.1:8000"


st.markdown(
    """
<style>
html, body, .stApp {
    background: #F4F6F8;
    color: #1C2B3A;
    font-family: Arial, sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 1.5rem 2.5rem 3rem;
    max-width: 100%;
}

.topbar {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.title {
    font-size: 22px;
    font-weight: 700;
    color: #1C2B3A;
}

.subtitle {
    font-size: 12px;
    color: #6B7280;
    margin-top: 4px;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 10px;
    padding: 20px;
}

.metric-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #6B7280;
    font-weight: 700;
    letter-spacing: 0.06em;
}

.metric-value {
    font-size: 32px;
    font-weight: 800;
    margin-top: 8px;
}

.section-title {
    margin-top: 30px;
    margin-bottom: 14px;
    font-size: 13px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #374151;
}

.card {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 14px;
}

.card-title {
    font-size: 16px;
    font-weight: 800;
}

.card-sub {
    color: #6B7280;
    font-size: 12px;
    margin-bottom: 12px;
}

.badge {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
}

.high { background: #FDE2E2; color: #B91C1C; }
.medium { background: #FEF3C7; color: #92400E; }
.low { background: #D1FAE5; color: #065F46; }
.normal { background: #E5E7EB; color: #374151; }

.footer {
    margin-top: 36px;
    padding-top: 14px;
    border-top: 1px solid #DDE3EA;
    color: #6B7280;
    font-size: 11px;
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
        if value is None:
            return default
        return float(value)
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
    text = str(text or "No action required. Continue monitoring.")
    text = text.replace("(100.0%)", "(99.9%+)")
    text = text.replace("(0.0%)", "(<0.5%)")
    return text


def supplier_name(row):
    return str(row.get("supplier_name") or row.get("supplier_code") or "Unknown")


def risk_badge(level):
    level = str(level or "").upper()

    if level == "HIGH_RISK":
        return '<span class="badge high">High</span>'

    if level == "MEDIUM_RISK":
        return '<span class="badge medium">Medium</span>'

    if level == "LOW_RISK":
        return '<span class="badge low">Low</span>'

    return f'<span class="badge normal">{level}</span>'


def warning_badge(status):
    status = str(status or "").upper()

    if status == "CRITICAL_WARNING":
        return '<span class="badge high">Critical Warning</span>'

    if status == "WARNING":
        return '<span class="badge medium">Warning</span>'

    if status == "WATCHLIST":
        return '<span class="badge medium">Watchlist</span>'

    return '<span class="badge low">Stable</span>'


@st.cache_data(ttl=30)
def fetch_supplier_data(period):
    response = requests.get(
        f"{API_URL}/supplier-predictions",
        params={"period": period},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.title("Afinetrip")
    st.caption("Supplier Risk Management")

    reporting_period = st.selectbox(
        "Reporting Period",
        list(REPORTING_PERIODS.keys()),
    )

    risk_filter = st.selectbox(
        "Risk Classification",
        ["All", "HIGH_RISK", "MEDIUM_RISK", "LOW_RISK"],
    )

    warning_filter = st.selectbox(
        "Warning Status",
        ["All", "CRITICAL_WARNING", "WARNING", "WATCHLIST", "STABLE"],
    )

    anomaly_only = st.checkbox("Show anomaly suppliers only")

    supplier_search = st.text_input(
        "Search Supplier",
        placeholder="Supplier name or code",
    )

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


try:
    data = fetch_supplier_data(REPORTING_PERIODS[reporting_period])
except Exception as error:
    st.error(f"Unable to connect to FastAPI service: {error}")
    st.info("Run this first: python -m uvicorn app.main:app --reload --port 8000")
    st.stop()


summary = data.get("summary", {})
df = pd.DataFrame(data.get("suppliers", []))

if df.empty:
    st.warning("No supplier prediction records found.")
    st.stop()


required_cols = {
    "supplier_code": "",
    "supplier_name": "",
    "risk_score": 0,
    "risk_level": "LOW_RISK",
    "predicted_risk": "LOW_RISK",
    "prediction_probability": 0,
    "future_instability_probability": 0,
    "future_instability_percentage": None,
    "early_warning_status": "STABLE",
    "future_recommendation": "No action required. Continue monitoring.",
    "anomaly_status": "NORMAL",
    "anomaly_score": 0,
    "total_bookings": 0,
    "failure_rate": 0,
    "pending_rate": 0,
    "process_error_rate": 0,
    "search_failure_rate": 0,
    "wallet_risk_rate": 0,
}

for col, default in required_cols.items():
    if col not in df.columns:
        df[col] = default


df["display_probability"] = df.apply(
    lambda row: (
        row["future_instability_percentage"] / 100
        if pd.notna(row.get("future_instability_percentage"))
        else row["future_instability_probability"]
    ),
    axis=1,
)

filtered = df.copy()

if risk_filter != "All":
    filtered = filtered[filtered["risk_level"] == risk_filter]

if warning_filter != "All":
    filtered = filtered[filtered["early_warning_status"] == warning_filter]

if anomaly_only:
    filtered = filtered[filtered["anomaly_status"] == "ANOMALY"]

if supplier_search:
    mask = (
        filtered["supplier_code"].astype(str).str.contains(
            supplier_search,
            case=False,
            na=False,
        )
        | filtered["supplier_name"].astype(str).str.contains(
            supplier_search,
            case=False,
            na=False,
        )
    )
    filtered = filtered[mask]


st.markdown(
    f"""
<div class="topbar">
    <div>
        <div class="title">Supplier Risk Management</div>
        <div class="subtitle">Afinetrip · Risk outlook for next 7 days</div>
    </div>
    <div class="subtitle">
        {datetime.now().strftime("%d %b %Y, %H:%M")}<br>
        Period: {reporting_period}
    </div>
</div>
""",
    unsafe_allow_html=True,
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">Suppliers Monitored</div>
    <div class="metric-value">{summary.get("total_suppliers", len(df))}</div>
</div>
""",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">Critical Warnings</div>
    <div class="metric-value">{summary.get("critical_future_warnings", 0)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">High Risk Suppliers</div>
    <div class="metric-value">{summary.get("high_risk_suppliers", 0)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">Anomalies</div>
    <div class="metric-value">{summary.get("anomaly_suppliers", 0)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


st.markdown(
    '<div class="section-title">Suppliers Requiring Immediate Attention</div>',
    unsafe_allow_html=True,
)

critical_df = filtered[
    filtered["early_warning_status"] == "CRITICAL_WARNING"
].sort_values("display_probability", ascending=False)

if critical_df.empty:
    st.success("All suppliers are currently within acceptable risk limits.")
else:
    for _, row in critical_df.head(3).iterrows():
        st.markdown(
            f"""
<div class="card">
    <div class="card-title">{supplier_name(row)}</div>
    <div class="card-sub">Supplier Code: {row.get("supplier_code")}</div>
    <p><b>Risk Probability:</b> {fmt_pct(row.get("display_probability"))}</p>
    <p><b>Risk Classification:</b> {risk_badge(row.get("risk_level"))}</p>
    <p><b>Warning Status:</b> {warning_badge(row.get("early_warning_status"))}</p>
    <p><b>Anomaly Status:</b> {row.get("anomaly_status")}</p>
    <p><b>Recommended Action:</b> {clean_text(row.get("future_recommendation"))}</p>
</div>
""",
            unsafe_allow_html=True,
        )


st.markdown(
    '<div class="section-title">Supplier Register</div>',
    unsafe_allow_html=True,
)

if filtered.empty:
    st.info("No supplier records match your filters.")
else:
    reg = filtered.copy()

    reg["Supplier"] = reg.apply(
        lambda row: f"{supplier_name(row)} ({row.get('supplier_code')})",
        axis=1,
    )

    reg["Risk Classification"] = reg["risk_level"].replace(
        {
            "HIGH_RISK": "High",
            "MEDIUM_RISK": "Medium",
            "LOW_RISK": "Low",
        }
    )

    reg["Risk Probability"] = reg["display_probability"].apply(fmt_pct)

    reg["Warning Status"] = reg["early_warning_status"].replace(
        {
            "CRITICAL_WARNING": "Critical Warning",
            "WARNING": "Warning",
            "WATCHLIST": "Watchlist",
            "STABLE": "Stable",
        }
    )

    reg["Anomaly Status"] = reg["anomaly_status"]

    reg["Recommended Action"] = reg["future_recommendation"].apply(clean_text)

    table = reg[
        [
            "Supplier",
            "Risk Classification",
            "Risk Probability",
            "Warning Status",
            "Anomaly Status",
            "Recommended Action",
        ]
    ].copy()

    table["_sort_probability"] = reg["display_probability"]

    table = table.sort_values(
        "_sort_probability",
        ascending=False,
    ).drop(columns=["_sort_probability"])

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )


st.markdown(
    '<div class="section-title">Supplier Profile</div>',
    unsafe_allow_html=True,
)

if not filtered.empty:
    profile_options = (
        filtered.sort_values("display_probability", ascending=False)
        .apply(
            lambda row: f"{supplier_name(row)} — {row.get('supplier_code')}",
            axis=1,
        )
        .tolist()
    )

    selected = st.selectbox(
        "Select supplier",
        profile_options,
        label_visibility="collapsed",
    )

    selected_code = selected.split("—")[-1].strip()
    selected_row = filtered[
        filtered["supplier_code"].astype(str) == selected_code
    ].iloc[0]

    st.markdown(
        f"""
<div class="card">
    <div class="card-title">{supplier_name(selected_row)}</div>
    <div class="card-sub">Supplier Code: {selected_row.get("supplier_code")}</div>
    <p><b>Risk Score:</b> {to_num(selected_row.get("risk_score")):.2f}</p>
    <p><b>Risk Probability:</b> {fmt_pct(selected_row.get("display_probability"))}</p>
    <p><b>Risk Classification:</b> {risk_badge(selected_row.get("risk_level"))}</p>
    <p><b>Warning Status:</b> {warning_badge(selected_row.get("early_warning_status"))}</p>
    <p><b>Total Bookings:</b> {int(to_num(selected_row.get("total_bookings")))}</p>
    <p><b>Failure Rate:</b> {fmt_pct(selected_row.get("failure_rate"))}</p>
    <p><b>Pending Rate:</b> {fmt_pct(selected_row.get("pending_rate"))}</p>
    <p><b>Process Error Rate:</b> {fmt_pct(selected_row.get("process_error_rate"))}</p>
    <p><b>Search Failure Rate:</b> {fmt_pct(selected_row.get("search_failure_rate"))}</p>
    <p><b>Wallet Risk Rate:</b> {fmt_pct(selected_row.get("wallet_risk_rate"))}</p>
    <p><b>Recommended Action:</b> {clean_text(selected_row.get("future_recommendation"))}</p>
</div>
""",
        unsafe_allow_html=True,
    )


st.markdown(
    f"""
<div class="footer">
    Afinetrip Pvt. Ltd. · Supplier Risk Management · Internal Use Only<br>
    Last refreshed: {datetime.now().strftime("%d %b %Y, %H:%M")}
</div>
""",
    unsafe_allow_html=True,
)