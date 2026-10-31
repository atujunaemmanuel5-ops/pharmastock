"""PharmaStock AI pharmacy workspace.

The dashboard is deliberately presentation-only: all forecasts, stock signals,
and dispensing decisions come from the FastAPI service.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="PharmaStock AI", page_icon="⚕", layout="wide", initial_sidebar_state="expanded")

API_URL = os.getenv("PHARMASTOCK_API_URL", os.getenv("API_URL", "http://127.0.0.1:8000")).rstrip("/")


def api_get(path: str, **params):
    response = requests.get(f"{API_URL}{path}", params=params or None, timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_URL}{path}", json=payload, timeout=30)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(str(detail))
    return response.json()


def api_upload(uploaded_file):
    response = requests.post(
        f"{API_URL}/upload",
        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")},
        timeout=60,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(str(detail))
    return response.json()


@st.cache_data(ttl=30, show_spinner=False)
def get_products():
    return api_get("/products")


@st.cache_data(ttl=30, show_spinner=False)
def get_drugs():
    return api_get("/inventory/drugs")


@st.cache_data(ttl=30, show_spinner=False)
def get_recommendations():
    return api_get("/recommendations")


@st.cache_data(ttl=30, show_spinner=False)
def get_expiry():
    return api_get("/inventory/expiry")


@st.cache_data(ttl=30, show_spinner=False)
def get_velocity():
    return api_get("/inventory/velocity")


def inject_styles():
    st.markdown(
        """
        <style>
        :root {
          --navy: #123047;
          --navy-2: #24536a;
          --teal: #0b9f95;
          --teal-soft: #e4f7f4;
          --coral: #e77c6f;
          --ink: #203442;
          --muted: #718391;
          --line: #dce7ed;
          --canvas: #f5f8fb;
          --danger: #c54f5d;
          --danger-soft: #fff0f1;
          --warning: #b7791f;
          --warning-soft: #fff7e7;
          --success: #167c61;
          --success-soft: #e7f7f0;
        }
        .stApp { background: radial-gradient(circle at 78% -10%, #e9f8f6 0, transparent 28%), var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #102f44 0%, #123b53 62%, #0d2a3e 100%); border-right: 0; box-shadow: 8px 0 26px rgba(13,42,62,.08); }
        [data-testid="stSidebar"] * { color: #eaf4f7; }
        [data-testid="stSidebar"] .stRadio label { color: #d6e7ed; }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: 6px; }
        [data-testid="stSidebar"] .stRadio label p { font-size: 0.93rem; }
        .main .block-container { max-width: 1440px; padding: 2.4rem 3.4rem 4rem; }
        .brand-mark { display:flex; align-items:center; gap:12px; margin-bottom:28px; }
        .brand-icon { width:44px; height:44px; border-radius:15px; display:flex; align-items:center; justify-content:center; background:linear-gradient(145deg,#effffb,#c9f2ec); color:var(--teal); box-shadow:0 8px 22px rgba(0,0,0,.12); }
        .brand-icon svg { width:25px; height:25px; }
        .brand-name { font-weight:800; letter-spacing:-.4px; font-size:1.05rem; }
        .brand-sub { color:#a9cad3; font-size:.73rem; margin-top:2px; }
        .sidebar-label { color:#8fb1bd; font-size:.69rem; text-transform:uppercase; letter-spacing:1.4px; margin:20px 0 8px; font-weight:700; }
        .sidebar-status { border:1px solid rgba(215,241,242,.18); border-radius:14px; padding:13px; margin-top:25px; background:rgba(255,255,255,.06); }
        .sidebar-status small { color:#a9cad3; display:block; margin-bottom:5px; }
        .sidebar-status strong { color:#e9fffa; }
        .topline { display:flex; justify-content:space-between; align-items:center; margin-bottom:26px; padding-bottom:18px; border-bottom:1px solid rgba(220,231,237,.85); }
        .eyebrow { color:var(--teal); font-weight:800; letter-spacing:1.8px; text-transform:uppercase; font-size:.69rem; margin-bottom:7px; }
        h1 { color:var(--navy); letter-spacing:-1.35px; font-size:2.35rem !important; margin:0 !important; }
        h2, h3 { color:var(--navy); letter-spacing:-.4px; }
        .page-intro { color:var(--muted); font-size:1rem; margin:.45rem 0 1.5rem; }
        .user-pill { border:1px solid #cfe7e4; background:#f5fffd; border-radius:24px; padding:9px 14px; color:#14766f; font-size:.78rem; font-weight:800; box-shadow:0 4px 14px rgba(11,159,149,.07); }
        .notice { padding:13px 16px; border-radius:13px; border:1px solid #f1dca7; background:var(--warning-soft); color:#765115; font-size:.86rem; margin: 0 0 22px; }
        .notice strong { color:#62420f; }
        .metric-card { background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:18px; padding:18px 19px; min-height:114px; box-shadow:0 7px 22px rgba(27,65,89,.055); transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
        .metric-card:hover { transform:translateY(-2px); border-color:#b6ddd9; box-shadow:0 12px 28px rgba(27,65,89,.10); }
        .metric-label { color:var(--muted); font-size:.77rem; font-weight:700; text-transform:uppercase; letter-spacing:.7px; }
        .metric-value { color:var(--navy); font-weight:800; font-size:1.75rem; margin-top:8px; letter-spacing:-.5px; }
        .metric-help { color:var(--muted); font-size:.76rem; margin-top:3px; }
        .section-head { display:flex; justify-content:space-between; align-items:end; margin:28px 0 12px; }
        .section-head h3 { margin:0; font-size:1.2rem; }
        .section-head p { margin:0; color:var(--muted); font-size:.82rem; }
        .panel { background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:19px; padding:20px; box-shadow:0 7px 22px rgba(27,65,89,.05); }
        .status-card { border-radius:16px; padding:18px 20px; border:1px solid; margin:13px 0 18px; }
        .status-card h3 { margin:0 0 4px; font-size:1.25rem; }
        .status-card p { margin:0; font-size:.9rem; }
        .status-ok { background:var(--success-soft); border-color:#b9e5d2; color:#12644f; }
        .status-info { background:#edf7fb; border-color:#c5e2ec; color:#145b75; }
        .status-warn { background:var(--warning-soft); border-color:#efd89f; color:#785313; }
        .status-danger { background:var(--danger-soft); border-color:#f1c3c8; color:#8c2737; }
        .reason { border-left:4px solid var(--warning); background:#fffaf0; padding:11px 13px; border-radius:8px; margin:7px 0; color:#5e4a25; font-size:.88rem; }
        .reason-danger { border-left-color:var(--danger); background:var(--danger-soft); color:#7d2c39; }
        .chip { display:inline-block; border-radius:20px; padding:5px 10px; background:var(--teal-soft); color:#08786f; font-size:.75rem; font-weight:800; margin:2px 5px 2px 0; }
        .empty { text-align:center; padding:34px 15px; color:var(--muted); border:1px dashed #cbd9e0; border-radius:14px; background:#fbfdfe; }
        .footer-note { color:#8b9ba6; font-size:.75rem; margin-top:28px; }
        div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); padding:14px 16px; border-radius:14px; }
        div[data-testid="stMetricLabel"] { color:var(--muted); }
        div[data-testid="stMetricValue"] { color:var(--navy); }
        .stButton > button { border-radius:11px; font-weight:750; border:1px solid #cbdde3; color:var(--navy); transition:all .18s ease; }
        .stButton > button:hover { border-color:var(--teal); color:var(--teal); transform:translateY(-1px); box-shadow:0 6px 14px rgba(11,159,149,.12); }
        .stButton > button[kind="primary"] { background:var(--teal); border-color:var(--teal); color:#fff; }
        .stButton > button[kind="primary"]:hover { background:#087f78; border-color:#087f78; color:#fff; }
        .stDownloadButton > button { border-radius:11px; }
        [data-testid="stSidebar"] .stRadio label:hover { background:rgba(255,255,255,.07); border-radius:10px; }
        [data-testid="stSidebar"] .stRadio label { padding:6px 8px; transition:background .18s ease; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, help_text: str = ""):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-help">{help_text}</div></div>',
        unsafe_allow_html=True,
    )


def section_head(title: str, description: str = ""):
    st.markdown(f'<div class="section-head"><div><h3>{title}</h3><p>{description}</p></div></div>', unsafe_allow_html=True)


def format_drug(item: dict) -> str:
    strength = f" · {item.get('strength')}" if item.get("strength") else ""
    form = f" · {item.get('form')}" if item.get("form") else ""
    return f"{item.get('generic_name', 'Unknown')} {strength}{form}  ·  {item.get('drug_id')}".replace("  ·  ", " · ")


def decision_style(decision: str) -> tuple[str, str, str]:
    if decision in {"BLOCK", "UNKNOWN", "STOP"}:
        return "status-danger", "Action blocked", "Do not dispense until the blocking issue is resolved."
    if decision in {"WARN", "STOP_OVERRIDDEN"}:
        return "status-warn", "Pharmacist review required", "Review the warnings before deciding whether to proceed."
    if decision == "INFO":
        return "status-info", "Can proceed with information", "Review the near-expiry or FEFO note before dispensing."
    return "status-ok", "Ready for confirmation", "The deterministic safety checks found no blocking issue."


def render_reasons(result: dict, drug_names: dict[str, str]):
    reasons = result.get("reasons", [])
    if not reasons:
        st.markdown('<div class="empty">No alerts were generated for this cart.</div>', unsafe_allow_html=True)
        return
    for reason in reasons:
        code = reason.get("code", "review")
        text = reason.get("message", "Review this alert.")
        label = code.replace("_", " ").title()
        extra = f" · {drug_names.get(reason.get('drug_id'), reason.get('drug_id', ''))}" if reason.get("drug_id") else ""
        klass = "reason-danger" if code in {"unknown_drug", "prescription_required", "no_unexpired_stock", "major_interaction"} else "reason"
        st.markdown(f'<div class="{klass}"><strong>{label}{extra}</strong><br>{text}</div>', unsafe_allow_html=True)


def render_dispense_result(result: dict, drug_names: dict[str, str]):
    decision = result.get("decision", "UNKNOWN")
    klass, title, detail = decision_style(decision)
    st.markdown(f'<div class="status-card {klass}"><h3>{title} · {decision}</h3><p>{detail}</p></div>', unsafe_allow_html=True)
    left, right = st.columns([1.2, 1])
    with left:
        section_head("Safety review", "Every alert comes from a deterministic rule or sourced interaction lookup.")
        render_reasons(result, drug_names)
    with right:
        section_head("Cart summary", "Items reviewed by the dispensing engine.")
        chips = "".join(f'<span class="chip">{drug_names.get(drug_id, drug_id)}</span>' for drug_id in result.get("drug_ids", []))
        st.markdown(chips or '<span class="chip">No items</span>', unsafe_allow_html=True)
        if result.get("interactions"):
            section_head("Interaction review", "Severity is shown plainly for pharmacist review.")
            interaction_rows = []
            for item in result["interactions"]:
                interaction_rows.append({
                    "Medicine A": drug_names.get(item.get("drug_a_id"), item.get("drug_a_id")),
                    "Medicine B": drug_names.get(item.get("drug_b_id"), item.get("drug_b_id")),
                    "Severity": item.get("severity", "Unknown"),
                    "Source": item.get("source_url") or item.get("source") or "Development mapping",
                })
            st.dataframe(pd.DataFrame(interaction_rows), hide_index=True, use_container_width=True, column_config={"Source": st.column_config.TextColumn(width="medium")})
        if result.get("fefo_picks"):
            section_head("FEFO pick", "Earliest unexpired batch recommended first.")
            fefo_rows = []
            for drug_id, item in result["fefo_picks"].items():
                fefo_rows.append({"Medicine": drug_names.get(drug_id, drug_id), "Batch": item.get("batch_no") or item.get("batch_id"), "Expiry": item.get("expiry_date"), "Units": item.get("qty_on_hand")})
            st.dataframe(pd.DataFrame(fefo_rows), hide_index=True, use_container_width=True)


def render_scenario_center(drugs: list[dict], recommendations: pd.DataFrame, expiry: pd.DataFrame):
    """Make the strongest product story one click away for a live presentation."""
    section_head("Demo scenario center", "Show the judge a complete pharmacy moment instead of a collection of disconnected charts.")
    names = {item["drug_id"]: format_drug(item) for item in drugs}
    scenarios = [
        "Prescription gate · blocked cart",
        "Interaction review · pharmacist stop",
        "Stockout planning · reorder risk",
        "Expiry action · FEFO priority",
    ]
    scenario = st.selectbox("Choose a scenario", scenarios, label_visibility="collapsed")
    if st.button("Run selected scenario", type="primary"):
        try:
            if scenario.startswith("Prescription"):
                output = api_post("/dispense/check", {"drug_ids": ["D029"]})
                st.session_state["demo_scenario_result"] = (scenario, output)
            elif scenario.startswith("Interaction"):
                output = api_post("/dispense/check", {"drug_ids": ["D047", "D005"]})
                st.session_state["demo_scenario_result"] = (scenario, output)
            elif scenario.startswith("Stockout"):
                if recommendations.empty:
                    st.warning("No reorder recommendations are available for this scenario.")
                else:
                    output = recommendations.sort_values(["risk_level", "reorder_quantity"], ascending=[True, False]).iloc[0].to_dict()
                    st.session_state["demo_scenario_result"] = (scenario, output)
            else:
                output = expiry[expiry["expiry_status"].isin(["Expired", "Critical", "Watch"])].head(6).copy()
                st.session_state["demo_scenario_result"] = (scenario, output)
        except (requests.RequestException, RuntimeError) as exc:
            st.error(f"Scenario could not be loaded: {exc}")
    stored = st.session_state.get("demo_scenario_result")
    if not stored or stored[0] != scenario:
        st.caption("Select a scenario and run it to see the product story.")
        return
    _, output = stored
    if scenario.startswith(("Prescription", "Interaction")):
        render_dispense_result(output, names)
    elif scenario.startswith("Stockout"):
        risk = output.get("risk_level", "Review")
        st.markdown(f'<div class="status-card status-warn"><h3>{output.get("product_group", "Product group")} needs planning attention · {risk} risk</h3><p>Current usable stock is {int(output.get("usable_stock", 0)):,} units against a lead-time demand estimate of {float(output.get("reorder_point", 0)):.1f} units.</p></div>', unsafe_allow_html=True)
        cols = st.columns(4)
        with cols[0]: metric_card("Usable stock", f"{int(output.get('usable_stock', 0)):,}", "Current unexpired stock")
        with cols[1]: metric_card("Daily demand", output.get("average_daily_demand", "—"), "Forecast estimate")
        with cols[2]: metric_card("Days cover", output.get("days_of_cover") or "∞", "Before replenishment")
        with cols[3]: metric_card("Suggested order", f"{int(output.get('reorder_quantity', 0)):,}", "Pack-rounded quantity")
    else:
        view = output.rename(columns={"generic_name": "Medicine", "batch_no": "Batch", "qty_on_hand": "Units", "expiry_date": "Expiry date", "expiry_status": "Status", "units_at_risk": "Units at risk"})
        st.markdown('<div class="status-card status-info"><h3>FEFO action queue</h3><p>Move the earliest-expiring usable batches first and remove expired stock from sale.</p></div>', unsafe_allow_html=True)
        st.dataframe(view[["Medicine", "Batch", "Units", "Expiry date", "Status", "Units at risk"]], hide_index=True, use_container_width=True)


def render_sidebar(health: dict) -> str:
    with st.sidebar:
        st.markdown('<div class="brand-mark"><div class="brand-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.15" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.1 19 6v5.2c0 4.6-2.9 8.2-7 9.7-4.1-1.5-7-5.1-7-9.7V6l7-2.9Z"/><path d="M12 8v8M8 12h8"/></svg></div><div><div class="brand-name">PharmaStock AI</div><div class="brand-sub">Pharmacy operations workspace</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
        page = st.radio("Navigate", ["Overview", "Dispensing", "Inventory", "Forecasting", "Data import", "Knowledge assistant"], label_visibility="collapsed")
        st.markdown('<div class="sidebar-status"><small>System status</small><strong>● API online</strong><br><small>Data service · local SQLite</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">Safety posture</div>', unsafe_allow_html=True)
        st.caption("Presentation decision support only. A licensed dispenser makes the final decision before any real-world use.")
        st.markdown('<div class="sidebar-label">Session</div>', unsafe_allow_html=True)
        st.caption(f"Connected to\n{API_URL}")
    return page


def render_header(page: str):
    titles = {
        "Overview": ("Pharmacy command center", "A focused view of stock health, demand, and today’s safety workload."),
        "Dispensing": ("Dispensing console", "Build a cart, review deterministic safety alerts, and confirm only after pharmacist review."),
        "Inventory": ("Inventory control", "Monitor expiry exposure, FEFO picks, and fast-moving medicines."),
        "Forecasting": ("Demand planning", "Translate historical demand into a short planning horizon and reorder view."),
        "Data import": ("Data import", "Bring in a validated product-group sales file without touching the medicine inventory."),
        "Knowledge assistant": ("Reference assistant", "Ask questions against the downloaded pharmacy guidance with page-level citations."),
    }
    eyebrow = "Pharmacy operations · decision support"
    title, subtitle = titles[page]
    st.markdown(f'<div class="topline"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><div class="page-intro">{subtitle}</div></div><div class="user-pill">Licensed dispenser workspace</div></div>', unsafe_allow_html=True)


def page_overview():
    products = get_products()
    drugs = get_drugs()
    recommendations = pd.DataFrame(get_recommendations())
    expiry = pd.DataFrame(get_expiry())
    velocity = pd.DataFrame(get_velocity())
    high_risk = int((recommendations.get("risk_level", pd.Series(dtype=str)) == "High").sum())
    medium_risk = int((recommendations.get("risk_level", pd.Series(dtype=str)) == "Medium").sum())
    critical = int((expiry.get("expiry_status", pd.Series(dtype=str)) == "Critical").sum())
    expired_units = int(expiry.loc[expiry.get("expiry_status", pd.Series(dtype=str)) == "Expired", "qty_on_hand"].sum()) if not expiry.empty else 0
    fast = int((velocity.get("velocity", pd.Series(dtype=str)) == "Fast").sum())

    cards = st.columns(4)
    with cards[0]: metric_card("Medicines catalogued", len(drugs), "Current pharmacy catalogue")
    with cards[1]: metric_card("High stockout risk", high_risk, "Product groups requiring attention")
    with cards[2]: metric_card("Expiry watchlist", critical, "Batches expiring within 30 days")
    with cards[3]: metric_card("Fast movers", fast, "Based on recent pharmacy demand")

    render_scenario_center(drugs, recommendations, expiry)

    section_head("Today’s attention", "Prioritised signals for the pharmacy team.")
    left, right = st.columns([1.15, .85])
    with left:
        if recommendations.empty:
            st.markdown('<div class="empty">No reorder recommendations are available.</div>', unsafe_allow_html=True)
        else:
            view = recommendations.copy()
            view["Product group"] = view["product_group"]
            view["Risk"] = view["risk_level"]
            view["Stock"] = view["usable_stock"]
            view["Days cover"] = view["days_of_cover"].fillna("∞")
            view["Reorder"] = view["reorder_quantity"]
            st.dataframe(view[["Product group", "Risk", "Stock", "Days cover", "Reorder"]], hide_index=True, use_container_width=True, column_config={"Risk": st.column_config.TextColumn(width="small"), "Days cover": st.column_config.TextColumn(width="small")})
            st.download_button("Download reorder report", recommendations.to_csv(index=False), "pharmastock_recommendations.csv", "text/csv")
    with right:
        st.markdown(f'<div class="panel"><div class="metric-label">Expiry exposure</div><div class="metric-value">{expired_units:,} units</div><p style="color:#718391;margin:5px 0 18px">Expired quantity is never offered for dispensing.</p><div class="metric-label">Near-term reorder signals</div><div style="font-size:1.45rem;font-weight:800;color:#123047;margin-top:6px">{high_risk + medium_risk}</div><p style="color:#718391;margin:5px 0 0">High and medium risk product groups.</p></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="metric-label">Presentation boundary</div><p style="margin:9px 0 0;color:#203442;font-weight:700">Built for a pharmacy demonstration</p><p style="margin:5px 0 0;color:#718391;font-size:.85rem">The workflow is ready to connect to approved pharmacy records when the concept moves beyond the demo.</p></div>', unsafe_allow_html=True)

    section_head("Expiry priority", "The first batches to inspect or move using FEFO.")
    if expiry.empty:
        st.markdown('<div class="empty">No expiry data available.</div>', unsafe_allow_html=True)
    else:
        priority = expiry[expiry["expiry_status"].isin(["Expired", "Critical", "Watch"])].copy().head(8)
        priority = priority.rename(columns={"generic_name": "Medicine", "batch_no": "Batch", "qty_on_hand": "Units", "expiry_date": "Expiry date", "expiry_status": "Status", "units_at_risk": "Units at risk"})
        st.dataframe(priority[["Medicine", "Batch", "Units", "Expiry date", "Status", "Units at risk"]], hide_index=True, use_container_width=True)


def page_dispensing():
    drugs = get_drugs()
    drug_names = {item["drug_id"]: format_drug(item) for item in drugs}
    drug_by_id = {item["drug_id"]: item for item in drugs}
    label_to_id = {format_drug(item): item["drug_id"] for item in drugs}
    st.markdown('<div class="notice"><strong>Dispense review:</strong> select the complete medicine cart first. The Dispense action checks every pair, prescription gate, stock batch, and FEFO recommendation together.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.05], gap="large")
    with left:
        section_head("Create a dispense cart", "Select medicines exactly as they appear on the request.")
        search = st.text_input("Find a medicine", placeholder="Search generic name or drug ID", label_visibility="collapsed")
        options = [label for label in label_to_id if not search or search.lower() in label.lower()]
        selected = st.multiselect("Medicines in cart", options, placeholder="Choose one or more medicines")
        prescription = st.text_input("Prescription reference", placeholder="Enter reference if required")
        override = st.text_area("Override reason", placeholder="Required only when overriding a major interaction", height=86)
        check = st.button("Dispense", type="primary", use_container_width=True)
        if check:
            if not selected:
                st.error("Add at least one medicine to the cart.")
            else:
                try:
                    st.session_state["last_dispense"] = api_post("/dispense/check", {"drug_ids": [label_to_id[item] for item in selected], "prescription_reference": prescription or None, "override_reason": override or None})
                    st.session_state["dispense_payload"] = {"drug_ids": [label_to_id[item] for item in selected], "prescription_reference": prescription or None, "override_reason": override or None}
                except (requests.RequestException, RuntimeError) as exc:
                    st.error(f"Safety check failed: {exc}")
        if selected:
            section_head("Current cart", f"{len(selected)} medicine(s) selected")
            cart_rows = []
            for label in selected:
                item = drug_by_id[label_to_id[label]]
                cart_rows.append({"Medicine": item.get("generic_name"), "Strength": item.get("strength") or "—", "Form": item.get("form") or "—", "Medicine ID": item.get("drug_id")})
            st.dataframe(pd.DataFrame(cart_rows), hide_index=True, use_container_width=True)
    with right:
        section_head("Decision panel", "The result will appear here after the safety check.")
        result = st.session_state.get("last_dispense")
        if not result:
            st.markdown('<div class="empty"><strong>Ready when you are</strong><br>Build a cart on the left and run the safety check.</div>', unsafe_allow_html=True)
        else:
            render_dispense_result(result, drug_names)
            if result.get("can_confirm"):
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Complete dispense", type="primary", use_container_width=True):
                    try:
                        confirmed = api_post("/dispense/confirm", st.session_state["dispense_payload"])
                        st.session_state["last_dispense"] = confirmed
                        st.success("Dispense confirmation recorded in the audit log.")
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(f"Confirmation failed: {exc}")


def page_inventory():
    expiry = pd.DataFrame(get_expiry())
    velocity = pd.DataFrame(get_velocity())
    section_head("Inventory overview", "Use the tabs to move from stock velocity to expiry action.")
    tabs = st.tabs(["Expiry & FEFO", "Velocity"])
    with tabs[0]:
        if expiry.empty:
            st.markdown('<div class="empty">No expiry records available.</div>', unsafe_allow_html=True)
        else:
            critical = int((expiry["expiry_status"] == "Critical").sum())
            expired = int((expiry["expiry_status"] == "Expired").sum())
            at_risk = int(expiry["units_at_risk"].sum())
            cols = st.columns(3)
            with cols[0]: metric_card("Expired batches", expired, "Never dispense these batches")
            with cols[1]: metric_card("Critical batches", critical, "Expiry within 30 days")
            with cols[2]: metric_card("Units at risk", f"{at_risk:,}", "Expected not to sell before expiry")
            status = st.multiselect("Show statuses", ["Expired", "Critical", "Watch", "OK"], default=["Expired", "Critical", "Watch"])
            view = expiry[expiry["expiry_status"].isin(status)].copy()
            view = view.rename(columns={"generic_name": "Medicine", "drug_id": "Drug ID", "batch_no": "Batch", "qty_on_hand": "Units", "expiry_date": "Expiry date", "days_to_expiry": "Days left", "expiry_status": "Status", "is_fefo_pick": "FEFO pick", "units_at_risk": "Units at risk"})
            columns = ["Medicine", "Drug ID", "Batch", "Units", "Expiry date", "Days left", "Status", "FEFO pick", "Units at risk"]
            st.dataframe(view[columns], hide_index=True, use_container_width=True, column_config={"Expiry date": st.column_config.DateColumn(format="DD MMM YYYY"), "Units": st.column_config.NumberColumn(format="%d"), "Days left": st.column_config.NumberColumn(format="%d")})
            st.download_button("Download expiry report", expiry.to_csv(index=False), "pharmastock_expiry.csv", "text/csv")
    with tabs[1]:
        if velocity.empty:
            st.markdown('<div class="empty">No velocity records available.</div>', unsafe_allow_html=True)
        else:
            fast = int((velocity["velocity"] == "Fast").sum())
            rising = int((velocity["trend"] == "Rising").sum())
            cols = st.columns(3)
            with cols[0]: metric_card("Fast movers", fast, "Highest recent daily volume")
            with cols[1]: metric_card("Rising demand", rising, "Short window above baseline")
            with cols[2]: metric_card("Tracked medicines", len(velocity), "Current pharmacy catalogue")
            filter_velocity = st.multiselect("Velocity classes", ["Fast", "Medium", "Slow"], default=["Fast", "Medium", "Slow"])
            view = velocity[velocity["velocity"].isin(filter_velocity)].copy().rename(columns={"generic_name": "Medicine", "drug_id": "Drug ID", "atc_level4": "Product group", "units_per_day_28d": "28-day units/day", "units_per_day_90d": "90-day units/day", "velocity": "Velocity", "trend": "Trend"})
            st.dataframe(view[["Medicine", "Drug ID", "Product group", "28-day units/day", "90-day units/day", "Velocity", "Trend"]], hide_index=True, use_container_width=True)


def page_forecasting():
    products = get_products()
    product_map = {f"{item['code']} · {item['description']}": item["code"] for item in products}
    section_head("Forecast workspace", "Explore demand history, the selected method, and the reorder recommendation together.")
    selected = st.selectbox("Product group", list(product_map), label_visibility="collapsed")
    code = product_map[selected]
    try:
        forecast = api_get(f"/forecast/{code}")
        recommendation = api_get(f"/reorder/{code}")
        history = pd.DataFrame(api_get(f"/products/{code}/history", days=90))
    except (requests.RequestException, RuntimeError) as exc:
        st.error(f"Forecast unavailable: {exc}")
        return
    cards = st.columns(4)
    with cards[0]: metric_card("Risk level", recommendation.get("risk_level", "—"), "Under current stock assumptions")
    with cards[1]: metric_card("Usable stock", f"{recommendation.get('usable_stock', 0):,}", "Unexpired units")
    with cards[2]: metric_card("Days of cover", recommendation.get("days_of_cover") if recommendation.get("days_of_cover") is not None else "∞", "Based on forecast demand")
    with cards[3]: metric_card("Suggested reorder", f"{recommendation.get('reorder_quantity', 0):,}", "Planning quantity")
    left, right = st.columns([1.5, .8])
    with left:
        section_head("Demand trajectory", "Historical group sales followed by the 7-day estimate.")
        past = history.rename(columns={"quantity": "Historical sales"})[["sale_date", "Historical sales"]].set_index("sale_date")
        future = pd.DataFrame(forecast["forecasts"]).rename(columns={"predicted_quantity": "Forecast"})[["sale_date", "Forecast"]].set_index("sale_date")
        chart = pd.concat([past, future], axis=1)
        st.line_chart(chart, color=["#8aa3b2", "#0a9b91"])
        st.caption(f"Selected method: {forecast.get('forecast_method', 'baseline')} · Historical group observations; forecast is an estimate.")
    with right:
        section_head("Planning recommendation", "The planner’s view of the selected group.")
        fields = [("Average daily demand", recommendation.get("average_daily_demand")), ("Lead time", f"{recommendation.get('lead_time_days')} days"), ("Reorder point", recommendation.get("reorder_point")), ("Safety stock", recommendation.get("safety_stock")), ("Pack size", recommendation.get("pack_size"))]
        for label, value in fields:
            st.markdown(f'<div style="display:flex;justify-content:space-between;border-bottom:1px solid #edf2f4;padding:10px 0"><span style="color:#718391">{label}</span><strong style="color:#123047">{value}</strong></div>', unsafe_allow_html=True)
        st.markdown('<br><div class="notice"><strong>Planning note:</strong> this is a planning heuristic for the selected pharmacy scenario, not a guarantee of future availability.</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    section_head("All product groups", "Prioritised by risk and suggested reorder quantity.")
    recommendations = pd.DataFrame(get_recommendations())
    view = recommendations.rename(columns={"product_group": "Product group", "risk_level": "Risk", "usable_stock": "Usable stock", "average_daily_demand": "Daily demand", "days_of_cover": "Days cover", "reorder_quantity": "Suggested reorder"})
    st.dataframe(view[["Product group", "Risk", "Usable stock", "Daily demand", "Days cover", "Suggested reorder"]], hide_index=True, use_container_width=True)


def page_assistant():
    section_head("Ask the reference assistant", "Answers are extractive and cite the local reference documents. It does not make dispensing decisions.")
    examples = ["What does the dispensing guideline say about dispensing medicines?", "What is the purpose of the Uganda Clinical Guidelines?", "What does the WHO list say about warfarin?"]
    st.markdown("<span style='color:#718391;font-size:.82rem'>Try a question:</span>", unsafe_allow_html=True)
    example_cols = st.columns(3)
    for column, example in zip(example_cols, examples):
        with column:
            if st.button(example, use_container_width=True):
                st.session_state["assistant_question"] = example
    question = st.text_input("Question", key="assistant_question", placeholder="Ask about a medicine, guideline, procurement, or dispensing practice")
    if st.button("Search reference library", type="primary"):
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                st.session_state["assistant_result"] = api_post("/ask", {"question": question.strip()})
            except (requests.RequestException, RuntimeError) as exc:
                st.error(f"Assistant unavailable: {exc}")
    result = st.session_state.get("assistant_result")
    if not result:
        st.markdown('<div class="empty" style="margin-top:20px"><strong>Reference library ready</strong><br>Ask a question to search the Uganda Clinical Guidelines, EMHSLU, and WHO Essential Medicines List.</div>', unsafe_allow_html=True)
        return
    if result.get("found"):
        st.markdown(f'<div class="panel" style="margin-top:20px"><div class="metric-label">Cited answer</div><p style="font-size:1.05rem;line-height:1.65;color:#203442;margin-bottom:0">{result.get("answer", "")}</p></div>', unsafe_allow_html=True)
        section_head("Sources", "Open the cited source in the local reference package when reviewing the answer.")
        for citation in result.get("citations", []):
            st.markdown(f'<div class="reason" style="border-left-color:#0a9b91"><strong>{citation.get("doc_name", "Reference document")}</strong> · page {citation.get("page", "—")}<br><span style="font-size:.8rem;color:#718391">{citation.get("section", "")}</span></div>', unsafe_allow_html=True)
    else:
        st.warning("Not found in the PharmaStock reference documents. Try a more specific question.")


def page_import():
    section_head("Import sales history", "Upload a validated Kaggle-format CSV to make it the active product-group sales history.")
    st.markdown('<div class="notice"><strong>Before you upload:</strong> this changes the active group-level sales history used by forecasts. It does not alter the medicine catalogue, batches, expiry dates, or drug-level sales.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Choose a sales CSV", type=["csv"], help="The API validates required dates, numeric values, groups, and calendar completeness.")
        if uploaded is not None:
            st.caption(f"Selected file · {uploaded.name} · {uploaded.size:,} bytes")
            try:
                preview = pd.read_csv(uploaded)
                st.dataframe(preview.head(8), hide_index=True, use_container_width=True)
            except Exception as exc:
                st.error(f"Could not preview this CSV: {exc}")
        submit = st.button("Validate and import", type="primary", use_container_width=True, disabled=uploaded is None)
        if submit and uploaded is not None:
            try:
                summary = api_upload(uploaded)
                get_products.clear()
                get_recommendations.clear()
                st.session_state["upload_summary"] = summary
                st.success("Sales history imported and persisted.")
            except (requests.RequestException, RuntimeError) as exc:
                st.error(f"Import rejected: {exc}")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="metric-label">Expected workflow</div><div style="margin-top:14px"><strong style="color:#123047">1 · Select</strong><p style="color:#718391;margin:4px 0 14px;font-size:.86rem">Choose the daily product-group sales CSV.</p><strong style="color:#123047">2 · Validate</strong><p style="color:#718391;margin:4px 0 14px;font-size:.86rem">The API rejects missing dates, invalid numbers, duplicate dates, and malformed groups.</p><strong style="color:#123047">3 · Activate</strong><p style="color:#718391;margin:4px 0 0;font-size:.86rem">Only a successful validation replaces the active group history used for forecasting.</p></div></div>', unsafe_allow_html=True)
        summary = st.session_state.get("upload_summary")
        if summary:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div class="panel"><div class="metric-label">Last import</div><div class="metric-value">{summary.get("rows", 0):,} rows</div><p style="color:#718391;margin:5px 0">{summary.get("first_date")} → {summary.get("last_date")}</p><p style="color:#167c61;font-weight:700;margin:12px 0 0">Persisted successfully</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_head("Add a medicine", "Extend the catalogue without editing CSV files. The new medicine can be selected in the dispensing cart immediately.")
    added = st.session_state.pop("medication_added", None)
    if added:
        st.success(f"{added.get('generic_name')} was added to the catalogue with {added.get('initial_stock', 0):,} opening units.")
    with st.form("add_medication_form", clear_on_submit=False):
        first, second, third = st.columns(3)
        with first:
            generic_name = st.text_input("Generic name *", placeholder="e.g. Ceftriaxone")
            strength = st.text_input("Strength", placeholder="e.g. 1 g")
            form = st.selectbox("Dosage form", ["tablet", "capsule", "injection", "cream", "syrup", "inhaler", "infusion", "other"])
        with second:
            atc_code = st.text_input("ATC code", placeholder="Optional")
            atc_level4 = st.text_input("ATC level 4", placeholder="Optional")
            pack_size = st.number_input("Pack size", min_value=1, max_value=100000, value=10, step=1)
        with third:
            lead_time = st.number_input("Lead time (days)", min_value=0, max_value=365, value=7, step=1)
            opening_stock = st.number_input("Opening stock (units)", min_value=0, value=100, step=1)
            expiry = st.date_input("Opening batch expiry", value=date.today().replace(year=date.today().year + 1))
        gate, source = st.columns(2)
        with gate:
            prescription_required = st.checkbox("Prescription reference required")
        with source:
            source_ref = st.text_input("Rule source/reference", placeholder="Required to enforce the gate")
        st.caption("A prescription gate without a source reference is stored for review but will not block dispensing automatically.")
        submit = st.form_submit_button("Add medicine to catalogue", type="primary", use_container_width=True)
    if submit:
        if not generic_name.strip():
            st.error("Generic name is required.")
        else:
            try:
                created = api_post("/inventory/medications", {
                    "generic_name": generic_name.strip(), "strength": strength or None, "form": form,
                    "atc_code": atc_code or None, "atc_level4": atc_level4 or None,
                    "pack_size": int(pack_size), "lead_time_days": int(lead_time), "initial_stock": int(opening_stock),
                    "expiry_date": expiry.isoformat(), "prescription_required": prescription_required,
                    "source_name": "User-entered catalogue rule" if prescription_required else None, "source_ref": source_ref or None,
                })
                get_drugs.clear()
                get_expiry.clear()
                get_velocity.clear()
                st.session_state["medication_added"] = created
                st.rerun()
            except (requests.RequestException, RuntimeError) as exc:
                st.error(f"Medicine could not be added: {exc}")


inject_styles()
try:
    health = api_get("/health")
except requests.RequestException:
    st.error("The API is unavailable. Start it with: uvicorn api.main:app --reload")
    st.stop()

page = render_sidebar(health)
render_header(page)

try:
    if page == "Overview":
        page_overview()
    elif page == "Dispensing":
        page_dispensing()
    elif page == "Inventory":
        page_inventory()
    elif page == "Forecasting":
        page_forecasting()
    elif page == "Data import":
        page_import()
    else:
        page_assistant()
except requests.RequestException as exc:
    st.error(f"Could not load pharmacy data from the API: {exc}")
except KeyError as exc:
    st.error(f"The API response is missing an expected field: {exc}")

st.markdown(f'<div class="footer-note">PharmaStock AI · pharmacy operations workspace · Last connected {datetime.now().strftime("%d %b %Y, %H:%M")}</div>', unsafe_allow_html=True)
