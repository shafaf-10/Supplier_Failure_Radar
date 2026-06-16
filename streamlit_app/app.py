from datetime import datetime

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Afinetrip · Supplier Failure Radar",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://127.0.0.1:8000"


st.markdown(
    """
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {background:#F9FAFB;}
.block-container {padding:2rem 3rem 4rem; max-width:100%;}
section[data-testid="stSidebar"] {background:#FFFFFF!important; border-right:1px solid #E5E7EB;}

.page-header {
    display:flex; justify-content:space-between; align-items:flex-end;
    padding-bottom:18px; border-bottom:1px solid #E5E7EB; margin-bottom:22px;
}
.page-title {font-size:26px; font-weight:800; color:#111827;}
.page-sub {font-size:13px; color:#6B7280; margin-top:5px;}
.page-meta {font-size:12px; color:#9CA3AF; text-align:right; line-height:1.8;}

.kpi-strip {
    display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:22px;
}
.kpi-card {
    background:#FFFFFF; border:1px solid #E5E7EB; border-radius:14px;
    padding:18px; box-shadow:0 1px 2px rgba(17,24,39,.04);
}
.kpi-label {
    font-size:10.5px; font-weight:800; color:#9CA3AF;
    text-transform:uppercase; letter-spacing:.07em; margin-bottom:8px;
}
.kpi-value {font-size:29px; font-weight:800;}
.kpi-hint {font-size:11px; color:#9CA3AF; margin-top:6px;}

.blue{color:#2563EB}.red{color:#DC2626}.yellow{color:#B45309}
.green{color:#059669}.purple{color:#7C3AED}.orange{color:#D97706}

.section-heading {
    font-size:13px; font-weight:800; color:#374151; margin:28px 0 14px;
    display:flex; align-items:center; gap:10px;
}
.section-heading::after {content:''; flex:1; height:1px; background:#E5E7EB;}

.alert-banner {
    background:#FEF2F2; border:1px solid #FECACA; border-radius:12px;
    padding:13px 16px; font-size:13px; font-weight:700; color:#991B1B; margin-bottom:18px;
}
.safe-banner {
    background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px;
    padding:13px 16px; font-size:13px; font-weight:700; color:#166534; margin-bottom:18px;
}

.alert-card {
    background:#FFFFFF; border:1px solid #E5E7EB; border-radius:14px;
    padding:18px 20px; min-height:205px; box-shadow:0 1px 2px rgba(17,24,39,.04);
}
.card-top {display:flex; justify-content:space-between; align-items:flex-start;}
.card-name {font-size:15px; font-weight:800; color:#111827;}
.card-code {font-size:11px; color:#9CA3AF; margin-top:2px; font-family:monospace;}
.card-divider {border:none; border-top:1px solid #F3F4F6; margin:13px 0;}
.card-grid {display:grid; grid-template-columns:repeat(2,1fr); gap:10px 18px;}
.card-label {font-size:11px; color:#9CA3AF; font-weight:700; margin-bottom:3px;}
.card-value {font-size:14px; font-weight:800; color:#111827;}
.card-action {
    font-size:12px; color:#374151; background:#F9FAFB; border:1px solid #E5E7EB;
    border-radius:8px; padding:9px 11px; margin-top:13px; line-height:1.5;
}

.badge {
    font-size:11px; font-weight:800; padding:4px 10px; border-radius:6px; display:inline-block;
}
.badge-high {background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;}
.badge-medium {background:#FFFBEB; color:#B45309; border:1px solid #FDE68A;}
.badge-low {background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;}
.badge-anomaly {background:#F5F3FF; color:#7C3AED; border:1px solid #DDD6FE;}

.detail-box {
    background:#FFFFFF; border:1px solid #E5E7EB; border-radius:14px;
    padding:18px; box-shadow:0 1px 2px rgba(17,24,39,.04);
}
.detail-title {font-size:15px; font-weight:800; color:#111827; margin-bottom:10px;}
.detail-grid {display:grid; grid-template-columns:repeat(4,1fr); gap:12px;}
.detail-item {background:#F9FAFB; border:1px solid #E5E7EB; border-radius:10px; padding:12px;}
.detail-label {font-size:11px; color:#9CA3AF; font-weight:700;}
.detail-value {font-size:18px; color:#111827; font-weight:800; margin-top:4px;}

.footer {
    margin-top:3rem; padding-top:16px; border-top:1px solid #E5E7EB;
    display:flex; justify-content:space-between; font-size:11px; color:#9CA3AF;
}
</style>
""",
    unsafe_allow_html=True,
)


def period_to_api(label: str) -> str:
    return {
        "All Time": "all",
        "Last 24 Hours": "24h",
        "Last 7 Days": "7d",
        "Last 30 Days": "30d",
        "Last 1 Year": "1y",
    }.get(label, "all")


@st.cache_data(ttl=60)
def fetch_data(period: str) -> dict:
    response = requests.get(
        f"{API_URL}/supplier-predictions",
        params={"period": period},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def to_num(value, default=0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def pct(value) -> str:
    return f"{round(to_num(value) * 100, 1)}%"


def risk_clean(value) -> str:
    return str(value or "LOW_RISK").upper()


def risk_label(value) -> str:
    return risk_clean(value).replace("_", " ")


def risk_badge(value) -> str:
    risk = risk_clean(value)
    if risk == "HIGH_RISK":
        return '<span class="badge badge-high">HIGH RISK</span>'
    if risk == "MEDIUM_RISK":
        return '<span class="badge badge-medium">MEDIUM RISK</span>'
    return '<span class="badge badge-low">LOW RISK</span>'


def anomaly_badge(value) -> str:
    val = str(value or "NORMAL").upper()
    if val == "ANOMALY":
        return '<span class="badge badge-anomaly">ANOMALY</span>'
    return '<span class="badge badge-low">NORMAL</span>'


def main_signal(row) -> str:
    signals = {
        "Booking": to_num(row.get("failure_rate")) + to_num(row.get("pending_rate")),
        "Process": to_num(row.get("process_error_rate")),
        "Refund": to_num(row.get("refund_rate")),
        "Credit": to_num(row.get("credit_rejection_rate")),
        "Search": to_num(row.get("search_failure_rate")),
        "Wallet": to_num(row.get("wallet_risk_rate")),
    }
    return max(signals, key=signals.get)


def short_action(row) -> str:
    risk = risk_clean(row.get("risk_level"))
    anomaly = str(row.get("anomaly_status", "NORMAL")).upper()
    signal = row.get("main_signal", "Booking")

    if anomaly == "ANOMALY":
        return f"Investigate abnormal {signal.lower()} behaviour immediately."
    if risk == "HIGH_RISK":
        return f"Reduce dependency and review {signal.lower()} failures."
    if risk == "MEDIUM_RISK":
        return f"Monitor {signal.lower()} trend and keep backup supplier ready."
    return "Continue normal monitoring."


def supplier_name(row) -> str:
    return str(row.get("supplier_name") or row.get("supplier_code") or "Unknown")


def build_card(row) -> str:
    return f"""<div class="alert-card">
<div class="card-top">
<div>
<div class="card-name">{supplier_name(row)}</div>
<div class="card-code">{row.get("supplier_code", "—")}</div>
</div>
{risk_badge(row.get("risk_level"))}
</div>
<hr class="card-divider">
<div class="card-grid">
<div>
<div class="card-label">Risk Score</div>
<div class="card-value">{round(to_num(row.get("risk_score")), 2)}</div>
</div>
<div>
<div class="card-label">Anomaly</div>
<div class="card-value">{str(row.get("anomaly_status", "NORMAL")).upper()}</div>
</div>
<div>
<div class="card-label">Bookings</div>
<div class="card-value">{int(to_num(row.get("total_bookings")))}</div>
</div>
<div>
<div class="card-label">Main Signal</div>
<div class="card-value">{row.get("main_signal", "—")}</div>
</div>
<div>
<div class="card-label">Failure Rate</div>
<div class="card-value">{pct(row.get("failure_rate"))}</div>
</div>
<div>
<div class="card-label">Pending Rate</div>
<div class="card-value">{pct(row.get("pending_rate"))}</div>
</div>
</div>
<div class="card-action">
<b>Admin action:</b><br>
{short_action(row)}
</div>
</div>"""


with st.sidebar:
    st.markdown(
        """
        <div style="padding-bottom:16px;border-bottom:1px solid #E5E7EB;margin-bottom:20px;">
            <div style="font-size:17px;font-weight:800;color:#111827;">Afinetrip</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Supplier Failure Radar</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    time_window = st.selectbox(
    "Time Window",
    ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"],
)

    risk_filter = st.selectbox(
        "Risk Level",
        ["ALL", "HIGH_RISK", "MEDIUM_RISK", "LOW_RISK"],
    )

    anomaly_only = st.checkbox("Anomalies only")

    supplier_search = st.text_input(
        "Search Supplier",
        placeholder="Supplier name or code...",
    )

    if st.button("Refresh Dashboard"):
        st.cache_data.clear()
        st.rerun()


try:
    data = fetch_data(period_to_api(time_window))
except Exception as error:
    st.error(f"Backend connection error: {error}")
    st.info("Start FastAPI: python -m uvicorn app.main:app --reload --port 8000")
    st.stop()


summary = data.get("summary", {})
df = pd.DataFrame(data.get("suppliers", []))

if df.empty:
    st.warning("No supplier prediction data found.")
    st.stop()

for col in [
    "supplier_code",
    "supplier_name",
    "risk_score",
    "risk_level",
    "anomaly_status",
    "total_bookings",
    "failure_rate",
    "pending_rate",
    "process_error_rate",
    "refund_rate",
    "credit_rejection_rate",
    "search_failure_rate",
    "wallet_risk_rate",
]:
    if col not in df.columns:
        df[col] = 0 if col not in ["supplier_code", "supplier_name", "risk_level", "anomaly_status"] else ""

df["main_signal"] = df.apply(main_signal, axis=1)
df["admin_action"] = df.apply(short_action, axis=1)

filtered = df.copy()

if risk_filter != "ALL":
    filtered = filtered[filtered["risk_level"] == risk_filter]

if anomaly_only:
    filtered = filtered[filtered["anomaly_status"] == "ANOMALY"]

if supplier_search:
    mask = (
        filtered["supplier_code"].astype(str).str.contains(supplier_search, case=False, na=False)
        | filtered["supplier_name"].astype(str).str.contains(supplier_search, case=False, na=False)
    )
    filtered = filtered[mask]

attention_df = filtered[
    (filtered["risk_level"].isin(["HIGH_RISK", "MEDIUM_RISK"]))
    | (filtered["anomaly_status"] == "ANOMALY")
].sort_values("risk_score", ascending=False)


st.markdown(
    f"""
<div class="page-header">
    <div>
        <div class="page-title">Supplier Failure Radar</div>
        <div class="page-sub">B2B airline supplier failure monitoring · {time_window}</div>
    </div>
    <div class="page-meta">
        {datetime.now().strftime('%a %d %b %Y, %H:%M')}<br>
        {summary.get("total_suppliers", len(df))} suppliers monitored
    </div>
</div>
""",
    unsafe_allow_html=True,
)


st.markdown(
    f"""
<div class="kpi-strip">
    <div class="kpi-card">
        <div class="kpi-label">Total Suppliers</div>
        <div class="kpi-value blue">{summary.get("total_suppliers", len(df))}</div>
        <div class="kpi-hint">Monitored suppliers</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">High Risk</div>
        <div class="kpi-value red">{summary.get("high_risk_suppliers", 0)}</div>
        <div class="kpi-hint">Immediate review</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Medium Risk</div>
        <div class="kpi-value yellow">{summary.get("medium_risk_suppliers", 0)}</div>
        <div class="kpi-hint">Monitor closely</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Anomalies</div>
        <div class="kpi-value purple">{summary.get("anomaly_suppliers", 0)}</div>
        <div class="kpi-hint">Unusual behaviour</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg Risk Score</div>
        <div class="kpi-value orange">{summary.get("average_risk_score", 0)}</div>
        <div class="kpi-hint">Overall exposure</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


if attention_df.empty:
    st.markdown(
        '<div class="safe-banner">✓ No suppliers require admin attention for this filter.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="alert-banner">⚠ {len(attention_df)} supplier(s) require admin attention.</div>',
        unsafe_allow_html=True,
    )


st.markdown(
    '<div class="section-heading">Top Supplier Alerts</div>',
    unsafe_allow_html=True,
)

if attention_df.empty:
    st.info("No alert cards to display.")
else:
    rows = list(attention_df.head(3).iterrows())
    cols = st.columns(3, gap="medium")

    for idx, (_, row) in enumerate(rows):
        with cols[idx]:
            st.markdown(
                build_card(row),
                unsafe_allow_html=True,
            )


st.markdown(
    '<div class="section-heading">Supplier Risk Overview</div>',
    unsafe_allow_html=True,
)

overview = filtered.copy()

overview["supplier"] = overview.apply(
    lambda r: f"{supplier_name(r)} ({r.get('supplier_code')})",
    axis=1,
)

overview["failure_rate"] = overview["failure_rate"].apply(pct)
overview["pending_rate"] = overview["pending_rate"].apply(pct)
overview["process_error_rate"] = overview["process_error_rate"].apply(pct)

overview = overview[
    [
        "supplier",
        "risk_level",
        "risk_score",
        "anomaly_status",
        "main_signal",
        "failure_rate",
        "pending_rate",
        "process_error_rate",
        "admin_action",
    ]
].sort_values("risk_score", ascending=False)

st.dataframe(
    overview,
    use_container_width=True,
    hide_index=True,
)


st.markdown(
    '<div class="section-heading">Selected Supplier Details</div>',
    unsafe_allow_html=True,
)

supplier_options = (
    filtered.sort_values("risk_score", ascending=False)
    .apply(
        lambda r: f"{supplier_name(r)} ({r['supplier_code']})",
        axis=1,
    )
    .tolist()
)

supplier_lookup = {
    f"{supplier_name(r)} ({r['supplier_code']})": r["supplier_code"]
    for _, r in filtered.iterrows()
}

selected_label = st.selectbox(
    "Select supplier for detailed signal view",
    supplier_options,
)

selected_supplier = supplier_lookup[selected_label]

selected = filtered[
    filtered["supplier_code"] == selected_supplier
].iloc[0]

st.markdown(
    f"""
<div class="detail-box">
    <div class="detail-title">{supplier_name(selected)} · {selected_supplier}</div>
    <div class="detail-grid">
        <div class="detail-item">
            <div class="detail-label">Failure Rate</div>
            <div class="detail-value">{pct(selected.get("failure_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Pending Rate</div>
            <div class="detail-value">{pct(selected.get("pending_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Process Error</div>
            <div class="detail-value">{pct(selected.get("process_error_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Refund Risk</div>
            <div class="detail-value">{pct(selected.get("refund_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Credit Rejection</div>
            <div class="detail-value">{pct(selected.get("credit_rejection_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Search Failure</div>
            <div class="detail-value">{pct(selected.get("search_failure_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Wallet Risk</div>
            <div class="detail-value">{pct(selected.get("wallet_risk_rate"))}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">Main Signal</div>
            <div class="detail-value">{selected.get("main_signal")}</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


st.markdown(
    """
<div class="footer">
    <span>Afinetrip Internal · Supplier Failure Radar</span>
    <span>Booking · Process · Refund · Credit · Search · Wallet Signals</span>
</div>
""",
    unsafe_allow_html=True,
)