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
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
 
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
 
html, body, .stApp {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: #F4F6F8;
    color: #1C2B3A;
    font-size: 13px;
    line-height: 1.5;
}
 
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2.5rem 3rem; max-width: 100%; }
 
/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #DDE3EA;
}
section[data-testid="stSidebar"] .block-container {
    padding: 1.75rem 1.25rem;
}
.sb-brand {
    padding-bottom: 16px;
    border-bottom: 1px solid #DDE3EA;
    margin-bottom: 22px;
}
.sb-brand-name { font-size: 15px; font-weight: 700; color: #1C2B3A; }
.sb-brand-sub  { font-size: 11px; color: #8B98A8; margin-top: 3px; font-weight: 400; }
.sb-group      { font-size: 10px; font-weight: 700; color: #8B98A8; text-transform: uppercase;
                 letter-spacing: 0.08em; margin: 22px 0 8px; }
 
/* ── Top navigation bar ── */
.topbar {
    background: #FFFFFF;
    border-bottom: 1px solid #DDE3EA;
    padding: 0 2.5rem;
    margin: 0 -2.5rem 28px;
    height: 56px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.topbar-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.topbar-logo {
    font-size: 15px;
    font-weight: 700;
    color: #1C2B3A;
    letter-spacing: -0.3px;
}
.topbar-sep  { width: 1px; height: 22px; background: #DDE3EA; }
.topbar-page { font-size: 13px; font-weight: 600; color: #4A5568; }
.topbar-meta {
    font-size: 11px;
    color: #8B98A8;
    text-align: right;
    line-height: 1.8;
}
 
/* ── Metric summary strip ── */
.metric-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #DDE3EA;
    border: 1px solid #DDE3EA;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 30px;
    box-shadow: 0 1px 4px rgba(28,43,58,0.05);
}
.metric-cell { background: #FFFFFF; padding: 20px 24px; }
.metric-label {
    font-size: 10px;
    font-weight: 600;
    color: #8B98A8;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    color: #1C2B3A;
}
.metric-value.primary { color: #1A56DB; }
.metric-value.danger  { color: #C81E1E; }
.metric-value.warning { color: #B45309; }
.metric-note {
    font-size: 11px;
    color: #8B98A8;
    margin-top: 7px;
}
 
/* ── Section title ── */
.section-title {
    font-size: 11px;
    font-weight: 700;
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding-bottom: 10px;
    border-bottom: 1px solid #DDE3EA;
    margin: 32px 0 18px;
}
 
/* ── Status banners ── */
.status-banner {
    padding: 11px 16px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 18px;
}
.status-banner.alert {
    background: #FDF2F2;
    border: 1px solid #F8B4B4;
    border-left: 4px solid #C81E1E;
    color: #9B1C1C;
}
.status-banner.clear {
    background: #F3FAF7;
    border: 1px solid #BCF0DA;
    border-left: 4px solid #057A55;
    color: #03543F;
}
 
/* ── Supplier alert cards ── */
.supplier-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 6px;
}
.supplier-card {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(28,43,58,0.05);
}
.sc-header {
    padding: 14px 16px 13px;
    border-bottom: 1px solid #F0F3F7;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.sc-header.sev-critical { border-top: 3px solid #C81E1E; }
.sc-header.sev-elevated { border-top: 3px solid #D97706; }
.sc-header.sev-review   { border-top: 3px solid #1A56DB; }
.sc-header.sev-stable   { border-top: 3px solid #057A55; }
.sc-supplier-name { font-size: 13px; font-weight: 700; color: #1C2B3A; }
.sc-supplier-code { font-size: 10.5px; color: #8B98A8; font-family: 'Courier New', monospace; margin-top: 3px; }
.sc-body {
    padding: 14px 16px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px 18px;
}
.sc-field-label { font-size: 10px; font-weight: 600; color: #8B98A8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 3px; }
.sc-field-value { font-size: 14px; font-weight: 700; color: #1C2B3A; }
.sc-field-value.danger { color: #C81E1E; }
.sc-footer {
    padding: 11px 16px;
    background: #F8FAFB;
    border-top: 1px solid #F0F3F7;
}
.sc-footer-label { font-size: 10px; font-weight: 700; color: #4A5568; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.sc-footer-text  { font-size: 11.5px; color: #374151; line-height: 1.55; }
 
/* ── Status badge ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}
.sb-critical { background: #FDF2F2; color: #C81E1E; border: 1px solid #F8B4B4; }
.sb-elevated { background: #FFF8F0; color: #92400E; border: 1px solid #FBBF24; }
.sb-review   { background: #EBF5FF; color: #1A56DB; border: 1px solid #A4CAFE; }
.sb-stable   { background: #F3FAF7; color: #057A55; border: 1px solid #84E1BC; }
.sb-irregular{ background: #FFF8F0; color: #92400E; border: 1px solid #FBBF24; }
.sb-normal   { background: #F8FAFB; color: #4A5568; border: 1px solid #DDE3EA; }
.sb-high     { background: #FDF2F2; color: #C81E1E; border: 1px solid #F8B4B4; }
.sb-medium   { background: #FFF8F0; color: #92400E; border: 1px solid #FBBF24; }
.sb-low      { background: #F3FAF7; color: #057A55; border: 1px solid #84E1BC; }
 
/* ── Supplier profile panel ── */
.profile-panel {
    background: #FFFFFF;
    border: 1px solid #DDE3EA;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(28,43,58,0.05);
}
.profile-header {
    padding: 16px 22px;
    background: #F8FAFB;
    border-bottom: 1px solid #DDE3EA;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.profile-supplier-name { font-size: 15px; font-weight: 700; color: #1C2B3A; }
.profile-supplier-meta { font-size: 11px; color: #8B98A8; margin-top: 3px; font-family: 'Courier New', monospace; }
.profile-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #DDE3EA;
}
.pm-cell  { background: #FFFFFF; padding: 18px 22px; }
.pm-label { font-size: 10px; font-weight: 600; color: #8B98A8; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px; }
.pm-value { font-size: 20px; font-weight: 700; color: #1C2B3A; }
.pm-value.danger { color: #C81E1E; }
.profile-action {
    padding: 14px 22px;
    border-top: 1px solid #DDE3EA;
    background: #FFFFFF;
}
.pa-label { font-size: 10px; font-weight: 700; color: #4A5568; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 5px; }
.pa-text  { font-size: 12.5px; color: #374151; line-height: 1.65; }
 
/* ── Page footer ── */
.page-footer {
    margin-top: 3.5rem;
    padding-top: 14px;
    border-top: 1px solid #DDE3EA;
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #8B98A8;
}
</style>
""", unsafe_allow_html=True)
API_URL = "http://127.0.0.1:8000"
 
REPORTING_PERIODS = {
    "All Time":       "all",
    "Last 24 Hours":  "24h",
    "Last 7 Days":    "7d",
    "Last 30 Days":   "30d",
    "Last 12 Months": "1y",
}
 
REQUIRED_FIELDS = {
    "supplier_code":                  "",
    "supplier_name":                  "",
    "risk_level":                     "LOW_RISK",
    "future_instability_probability": 0,
    "early_warning_status":           "STABLE",
    "future_recommendation":          "No action required. Continue standard monitoring.",
    "anomaly_status":                 "NORMAL",
    "total_bookings":                 0,
}
DISPLAY_LABELS = {
    "CRITICAL_WARNING": "Immediate Action Required",
    "WARNING":          "Elevated Risk",
    "WATCHLIST":        "Under Review",
    "STABLE":           "Operational",
    "ANOMALY":          "Irregular Pattern",
    "NORMAL":           "Within Normal Range",
    "HIGH_RISK":        "High",
    "MEDIUM_RISK":      "Medium",
    "LOW_RISK":         "Low",
}
BADGE_CLASS = {
    "CRITICAL_WARNING": "sb-critical",
    "WARNING":          "sb-elevated",
    "WATCHLIST":        "sb-review",
    "STABLE":           "sb-stable",
    "ANOMALY":          "sb-irregular",
    "NORMAL":           "sb-normal",
    "HIGH_RISK":        "sb-high",
    "MEDIUM_RISK":      "sb-medium",
    "LOW_RISK":         "sb-low",
}
CARD_SEVERITY = {
    "CRITICAL_WARNING": "sev-critical",
    "WARNING":          "sev-elevated",
    "WATCHLIST":        "sev-review",
    "STABLE":           "sev-stable",
}
ALERT_STATUS_MAP = {
    "Immediate Action Required": "CRITICAL_WARNING",
    "Elevated Risk":             "WARNING",
    "Under Review":              "WATCHLIST",
    "Operational":               "STABLE",
}
RISK_CLASS_MAP = {
    "High":   "HIGH_RISK",
    "Medium": "MEDIUM_RISK",
    "Low":    "LOW_RISK",
} 
def to_num(v, default=0.0):
    try:    return float(v or default)
    except: return default
 
def fmt_pct(v):
    return f"{round(to_num(v) * 100, 1)}%"
 
def supplier_name(row):
    return str(row.get("supplier_name") or row.get("supplier_code") or "Unknown")
 
def display_label(v):
    key = str(v or "").upper().strip()
    return DISPLAY_LABELS.get(key, str(v or "").replace("_", " ").title())
 
def status_badge(v):
    key = str(v or "").upper().strip()
    cls = BADGE_CLASS.get(key, "sb-normal")
    return f'<span class="status-badge {cls}">{display_label(key)}</span>'
 
def card_sev(status):
    return CARD_SEVERITY.get(str(status or "").upper(), "sev-stable")
 
def build_supplier_card(row):
    name = supplier_name(row)
    code = row.get("supplier_code", "—")
    sev  = card_sev(row.get("early_warning_status"))
    return f"""
<div class="supplier-card">
  <div class="sc-header {sev}">
    <div>
      <div class="sc-supplier-name">{name}</div>
      <div class="sc-supplier-code">{code}</div>
    </div>
    {status_badge(row.get("early_warning_status"))}
  </div>
  <div class="sc-body">
    <div>
      <div class="sc-field-label">Risk Probability</div>
      <div class="sc-field-value danger">{fmt_pct(row.get("future_instability_probability"))}</div>
    </div>
    <div>
      <div class="sc-field-label">Risk Classification</div>
      <div class="sc-field-value">{display_label(row.get("risk_level"))}</div>
    </div>
    <div>
      <div class="sc-field-label">Operational Status</div>
      <div class="sc-field-value">{display_label(row.get("early_warning_status"))}</div>
    </div>
    <div>
      <div class="sc-field-label">Behavioural Pattern</div>
      <div class="sc-field-value">{display_label(row.get("anomaly_status"))}</div>
    </div>
  </div>
  <div class="sc-footer">
    <div class="sc-footer-label">Recommended Action</div>
    <div class="sc-footer-text">{row.get("future_recommendation", "Monitor supplier performance closely.")}</div>
  </div>
</div>"""
@st.cache_data(ttl=60)
def fetch_supplier_data(period: str) -> dict:
    response = requests.get(
        f"{API_URL}/supplier-predictions",
        params={"period": period},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-name">Afinetrip</div>
        <div class="sb-brand-sub">Supplier Risk Management</div>
    </div>
    """, unsafe_allow_html=True)
 
    st.markdown('<div class="sb-group">Reporting Period</div>', unsafe_allow_html=True)
    reporting_period = st.selectbox(
        "Reporting Period",
        list(REPORTING_PERIODS.keys()),
        label_visibility="collapsed",
    )
 
    st.markdown('<div class="sb-group">Filters</div>', unsafe_allow_html=True)
    alert_filter = st.selectbox(
        "Operational Status",
        ["All Statuses", "Immediate Action Required", "Elevated Risk", "Under Review", "Operational"],
    )
    risk_filter = st.selectbox(
        "Risk Classification",
        ["All Levels", "High", "Medium", "Low"],
    )
    irregular_only = st.checkbox("Show irregular pattern suppliers only")
    supplier_search = st.text_input("Search Supplier", placeholder="Name or supplier code…")
 
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
try:
    data = fetch_supplier_data(REPORTING_PERIODS[reporting_period])
except Exception as e:
    st.error(f"Unable to connect to the data service: {e}")
    st.info("Ensure the API service is running: uvicorn app.main:app --port 8000")
    st.stop()
 
summary = data.get("summary", {})
df = pd.DataFrame(data.get("suppliers", []))
 
if df.empty:
    st.warning("No supplier records were returned for the selected period.")
    st.stop()
 
for col, default in REQUIRED_FIELDS.items():
    if col not in df.columns:
        df[col] = default 
filtered = df.copy()
 
if alert_filter != "All Statuses":
    api_val = ALERT_STATUS_MAP.get(alert_filter)
    if api_val:
        filtered = filtered[filtered["early_warning_status"] == api_val]
 
if risk_filter != "All Levels":
    api_val = RISK_CLASS_MAP.get(risk_filter)
    if api_val:
        filtered = filtered[filtered["risk_level"] == api_val]
 
if irregular_only:
    filtered = filtered[filtered["anomaly_status"] == "ANOMALY"]
 
if supplier_search:
    mask = (
        filtered["supplier_code"].astype(str).str.contains(supplier_search, case=False, na=False)
        | filtered["supplier_name"].astype(str).str.contains(supplier_search, case=False, na=False)
    )
    filtered = filtered[mask]
st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-logo">Afinetrip</div>
    <div class="topbar-sep"></div>
    <div class="topbar-page">Supplier Risk Management</div>
  </div>
  <div class="topbar-meta">
    {datetime.now().strftime('%A, %d %B %Y &nbsp;&middot;&nbsp; %H:%M')}<br>
    Period: {reporting_period} &nbsp;&middot;&nbsp; Risk Outlook: Next 7 Days
  </div>
</div>
""", unsafe_allow_html=True)
total_suppliers = summary.get("total_suppliers", len(df))
immediate_action = summary.get("critical_future_warnings", 0)
high_risk_count  = summary.get("high_risk_suppliers", 0)
irregular_count  = summary.get("anomaly_suppliers", 0)
 
st.markdown(f"""
<div class="metric-strip">
  <div class="metric-cell">
    <div class="metric-label">Suppliers Monitored</div>
    <div class="metric-value primary">{total_suppliers}</div>
    <div class="metric-note">Active in selected period</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Immediate Action Required</div>
    <div class="metric-value danger">{immediate_action}</div>
    <div class="metric-note">Within 7-day outlook</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">High Risk Suppliers</div>
    <div class="metric-value warning">{high_risk_count}</div>
    <div class="metric-note">Current risk classification</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Irregular Patterns</div>
    <div class="metric-value">{irregular_count}</div>
    <div class="metric-note">Behavioural deviation detected</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Suppliers Requiring Immediate Attention</div>',
    unsafe_allow_html=True,
)
 
critical_df = (
    filtered[filtered["early_warning_status"] == "CRITICAL_WARNING"]
    .sort_values("future_instability_probability", ascending=False)
)
 
if critical_df.empty:
    st.markdown(
        '<div class="status-banner clear">&#10003; &nbsp;All suppliers are currently operating within acceptable performance parameters.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-banner alert">&#9888; &nbsp;{len(critical_df)} supplier(s) have been flagged and require immediate operational review.</div>',
        unsafe_allow_html=True,
    )
    cards_html = '<div class="supplier-grid">'
    for _, row in critical_df.head(3).iterrows():
        cards_html += build_supplier_card(row)
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
st.markdown('<div class="section-title">Supplier Register</div>', unsafe_allow_html=True)
 
if filtered.empty:
    st.info("No supplier records match the selected filter criteria.")
else:
    reg = filtered.copy()
    reg["Supplier Name"]        = reg.apply(lambda r: f"{supplier_name(r)} ({r.get('supplier_code', '')})", axis=1)
    reg["Risk Classification"]  = reg["risk_level"].apply(display_label)
    reg["Risk Probability"]     = reg["future_instability_probability"].apply(fmt_pct)
    reg["Operational Status"]   = reg["early_warning_status"].apply(display_label)
    reg["Behavioural Pattern"]  = reg["anomaly_status"].apply(display_label)
    reg["Recommended Action"]   = reg["future_recommendation"]
 
    st.dataframe(
        reg[[
            "Supplier Name",
            "Risk Classification",
            "Risk Probability",
            "Operational Status",
            "Behavioural Pattern",
            "Recommended Action",
        ]].sort_values("Risk Probability", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
st.markdown('<div class="section-title">Supplier Profile</div>', unsafe_allow_html=True)
 
if filtered.empty:
    st.stop()
 
profile_options = (
    filtered.sort_values("future_instability_probability", ascending=False)
    .apply(lambda r: f"{supplier_name(r)}  —  {r['supplier_code']}", axis=1)
    .tolist()
)
profile_lookup = {
    f"{supplier_name(r)}  —  {r['supplier_code']}": r["supplier_code"]
    for _, r in filtered.iterrows()
}
 
selected = st.selectbox(
    "Select a supplier to view its full profile",
    profile_options,
    label_visibility="collapsed",
)
sel = filtered[filtered["supplier_code"] == profile_lookup[selected]].iloc[0]
 
st.markdown(f"""
<div class="profile-panel">
  <div class="profile-header">
    <div>
      <div class="profile-supplier-name">{supplier_name(sel)}</div>
      <div class="profile-supplier-meta">Supplier Code: {sel.get('supplier_code', '—')}</div>
    </div>
    {status_badge(sel.get("early_warning_status"))}
  </div>
  <div class="profile-metrics">
    <div class="pm-cell">
      <div class="pm-label">Risk Probability</div>
      <div class="pm-value danger">{fmt_pct(sel.get("future_instability_probability"))}</div>
    </div>
    <div class="pm-cell">
      <div class="pm-label">Risk Classification</div>
      <div class="pm-value">{display_label(sel.get("risk_level"))}</div>
    </div>
    <div class="pm-cell">
      <div class="pm-label">Behavioural Pattern</div>
      <div class="pm-value">{display_label(sel.get("anomaly_status"))}</div>
    </div>
    <div class="pm-cell">
      <div class="pm-label">Total Bookings</div>
      <div class="pm-value">{int(to_num(sel.get("total_bookings")))}</div>
    </div>
  </div>
  <div class="profile-action">
    <div class="pa-label">Recommended Action</div>
    <div class="pa-text">{sel.get("future_recommendation", "No action required at this time.")}</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown(f"""
<div class="page-footer">
  <span>Afinetrip Pvt. Ltd. &nbsp;&middot;&nbsp; Supplier Risk Management &nbsp;&middot;&nbsp; Internal Use Only</span>
  <span>Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')} &nbsp;&middot;&nbsp; Risk outlook: Next 7 days</span>
</div>
""", unsafe_allow_html=True)

