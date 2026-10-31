import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BookOpen,
  Boxes,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  FileUp,
  FlaskConical,
  LayoutDashboard,
  Menu,
  PackageCheck,
  Pill,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  TriangleAlert,
  Truck,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.message || `Request failed (${response.status})`);
  return body;
}

const moneyless = (value) => value === null || value === undefined || value === "" ? "—" : value;
const number = (value) => Number(value || 0).toLocaleString();
const dateLabel = (value) => value ? new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";

function LogoMark({ compact = false }) {
  return (
    <div className={`brand ${compact ? "brand-compact" : ""}`}>
      <div className="brand-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none">
          <path d="M16 3.8 26 8v7.2c0 6.3-4.1 11.2-10 13-5.9-1.8-10-6.7-10-13V8l10-4.2Z" stroke="currentColor" strokeWidth="2.1" strokeLinejoin="round" />
          <path d="M16 10v12M10 16h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>
      {!compact && <div><strong>PharmaStock</strong><span>AI pharmacy operations</span></div>}
    </div>
  );
}

const navItems = [
  ["overview", "Command center", LayoutDashboard],
  ["dispensing", "Dispensing", ClipboardCheck],
  ["inventory", "Inventory", Boxes],
  ["forecasting", "Demand planning", Activity],
  ["catalogue", "Medicine catalogue", Pill],
  ["assistant", "Reference assistant", BookOpen],
];

function Sidebar({ page, setPage, health }) {
  return (
    <aside className="sidebar">
      <LogoMark />
      <div className="sidebar-section-label">Workspace</div>
      <nav className="sidebar-nav">
        {navItems.map(([id, label, Icon]) => (
          <button key={id} className={`nav-item ${page === id ? "active" : ""}`} onClick={() => setPage(id)}>
            <Icon size={18} strokeWidth={1.8} />
            <span>{label}</span>
            {page === id && <ChevronRight size={15} className="nav-arrow" />}
          </button>
        ))}
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-status">
        <div className="status-orb"><ShieldCheck size={17} /></div>
        <div><strong>System online</strong><span>{health?.database || "Local data service"}</span></div>
        <span className="online-dot" />
      </div>
      <div className="sidebar-note">
        <span>Presentation workspace</span>
        <p>Decision support for pharmacy teams. Final dispensing decisions remain with a licensed professional.</p>
      </div>
      <div className="sidebar-footer"><LogoMark compact /> <span>v0.2 · Local workspace</span></div>
    </aside>
  );
}

function Topbar({ title, subtitle, onRefresh, loading }) {
  return (
    <header className="topbar">
      <div><div className="topbar-kicker">PHARMASTOCK / OPERATIONS</div><h1>{title}</h1><p>{subtitle}</p></div>
      <div className="topbar-actions">
        <span className="connection-pill"><span className="online-dot" /> API connected</span>
        <button className="icon-button" onClick={onRefresh} title="Refresh workspace" disabled={loading}><RefreshCw size={17} className={loading ? "spin" : ""} /></button>
        <div className="avatar">PH</div>
      </div>
    </header>
  );
}

function MetricCard({ icon: Icon, label, value, detail, tone = "teal" }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18} /></div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function Badge({ children, tone = "neutral" }) { return <span className={`badge badge-${tone}`}>{children}</span>; }

function riskTone(value) {
  const v = String(value || "").toLowerCase();
  return v === "high" || v === "expired" || v === "critical" ? "danger" : v === "medium" || v === "watch" ? "warning" : v === "low" || v === "ok" ? "success" : "neutral";
}

function EmptyState({ icon: Icon = PackageCheck, title, detail }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={22} /></div><strong>{title}</strong><span>{detail}</span></div>;
}

function AttentionRow({ icon: Icon, tone, title, detail, action, onClick }) {
  return <button className="attention-row" onClick={onClick}><div className={`attention-icon ${tone}`}><Icon size={18} /></div><div className="attention-copy"><strong>{title}</strong><span>{detail}</span></div><div className="attention-action">{action}<ArrowUpRight size={16} /></div></button>;
}

function Overview({ data, onPage, onScenario }) {
  const { drugs, recommendations, expiry, velocity } = data;
  const highRisk = recommendations.filter((x) => x.risk_level === "High");
  const mediumRisk = recommendations.filter((x) => x.risk_level === "Medium");
  const criticalExpiry = expiry.filter((x) => ["Expired", "Critical"].includes(x.expiry_status));
  const fast = velocity.filter((x) => x.velocity === "Fast");
  const scenarioOptions = [
    ["prescription", "Prescription gate", "Show a blocked prescription-only cart", ShieldCheck],
    ["interaction", "Interaction stop", "Show a multi-medicine safety review", TriangleAlert],
    ["stockout", "Reorder risk", "Show a planning recommendation", Truck],
    ["expiry", "Expiry action", "Show the FEFO priority queue", Clock3],
  ];
  return <>
    <section className="hero-strip"><div><div className="hero-overline"><Sparkles size={14} /> Today at a glance</div><h2>Make the next pharmacy decision with confidence.</h2><p>One workspace for safe dispensing, inventory pressure, and evidence-backed planning.</p></div><button className="primary-button hero-button" onClick={() => onPage("dispensing")}><ClipboardCheck size={17} /> Open dispensing console</button></section>
    <div className="metric-grid">
      <MetricCard icon={Pill} label="Medicines" value={number(drugs.length)} detail="Catalogue records" tone="teal" />
      <MetricCard icon={TriangleAlert} label="High stockout risk" value={number(highRisk.length)} detail="Product groups to review" tone="coral" />
      <MetricCard icon={Clock3} label="Expiry attention" value={number(criticalExpiry.length)} detail="Expired or within 30 days" tone="amber" />
      <MetricCard icon={Activity} label="Fast movers" value={number(fast.length)} detail="Recent demand velocity" tone="violet" />
    </div>
    <div className="content-grid overview-grid">
      <section className="surface attention-panel"><div className="section-title"><div><span className="eyebrow">Prioritised work</span><h2>Attention queue</h2></div><button className="text-button" onClick={() => onPage("inventory")}>View inventory <ChevronRight size={15} /></button></div>
        {highRisk.slice(0, 2).map((item) => <AttentionRow key={`r-${item.product_group}`} icon={TriangleAlert} tone="danger" title={`${item.product_group} may need replenishment`} detail={`${number(item.usable_stock)} usable units · ${moneyless(item.days_of_cover)} days cover`} action="Review" onClick={() => onPage("forecasting")} />)}
        {criticalExpiry.slice(0, 2).map((item) => <AttentionRow key={`e-${item.batch_id}`} icon={Clock3} tone="warning" title={`${item.generic_name} · ${item.expiry_status.toLowerCase()}`} detail={`${number(item.qty_on_hand)} units · batch ${item.batch_no} · ${dateLabel(item.expiry_date)}`} action="Inspect" onClick={() => onPage("inventory")} />)}
        {highRisk.length === 0 && criticalExpiry.length === 0 && <EmptyState title="No urgent attention items" detail="Your current workspace has no high-priority alerts." />}
      </section>
      <section className="surface scenario-panel"><div className="section-title"><div><span className="eyebrow">Presentation mode</span><h2>Scenario launcher</h2></div><Sparkles size={18} className="muted-icon" /></div><p className="section-intro">Show the complete product story in one click.</p><div className="scenario-list">{scenarioOptions.map(([id, label, detail, Icon]) => <button key={id} className="scenario-card" onClick={() => onScenario(id)}><span className="scenario-icon"><Icon size={18} /></span><span><strong>{label}</strong><small>{detail}</small></span><ChevronRight size={17} /></button>)}</div></section>
    </div>
    <section className="surface table-surface"><div className="section-title"><div><span className="eyebrow">Planning signals</span><h2>Reorder recommendations</h2></div><button className="text-button" onClick={() => onPage("forecasting")}>Open planning <ChevronRight size={15} /></button></div><RecommendationsTable rows={recommendations.slice(0, 8)} /></section>
  </>;
}

function RecommendationsTable({ rows }) {
  if (!rows.length) return <EmptyState title="No recommendations yet" detail="Planning signals will appear when sales and stock are available." />;
  return <div className="data-table"><div className="table-head"><span>Product group</span><span>Risk</span><span>Usable stock</span><span>Days cover</span><span>Suggested order</span><span /></div>{rows.map((row) => <div className="table-row" key={row.product_group}><strong>{row.product_group}</strong><Badge tone={riskTone(row.risk_level)}>{row.risk_level}</Badge><span>{number(row.usable_stock)}</span><span>{row.days_of_cover ?? "∞"}</span><strong>{number(row.reorder_quantity)}</strong><ChevronRight size={16} className="row-chevron" /></div>)}</div>;
}

function Dispensing({ drugs, result, onDispense, onComplete, busy }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState([]);
  const [prescription, setPrescription] = useState("");
  const [override, setOverride] = useState("");
  const drugMap = useMemo(() => Object.fromEntries(drugs.map((d) => [d.drug_id, d])), [drugs]);
  const filtered = drugs.filter((d) => `${d.generic_name} ${d.strength || ""} ${d.drug_id}`.toLowerCase().includes(query.toLowerCase()));
  const toggle = (id) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  const decision = result?.decision;
  const resultTone = decision === "OK" || decision === "INFO" ? "success" : ["WARN", "STOP_OVERRIDDEN"].includes(decision) ? "warning" : "danger";
  return <div className="dispensing-layout">
    <section className="surface cart-builder"><div className="section-title"><div><span className="eyebrow">Dispense safely</span><h2>Build the medicine cart</h2></div><Badge tone="neutral">{selected.length} selected</Badge></div><p className="section-intro">Select every medicine in the request before pressing Dispense. The engine checks the complete combination.</p>
      <div className="search-box"><Search size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search generic name, strength, or medicine ID" /></div>
      <div className="medicine-picker">{filtered.map((drug) => <button key={drug.drug_id} className={`medicine-option ${selected.includes(drug.drug_id) ? "selected" : ""}`} onClick={() => toggle(drug.drug_id)}><span className="medicine-symbol"><Pill size={16} /></span><span><strong>{drug.generic_name}</strong><small>{drug.strength || "Strength not specified"} · {drug.form || "Medicine"}</small></span>{selected.includes(drug.drug_id) ? <CheckCircle2 size={18} className="selected-check" /> : <Plus size={18} />}</button>)}</div>
      {selected.length > 0 && <div className="cart-preview"><div className="cart-preview-header"><strong>Current cart</strong><span>{selected.length} medicines</span></div>{selected.map((id) => <div className="cart-item" key={id}><span className="cart-item-name"><Pill size={15} />{drugMap[id]?.generic_name}<small>{drugMap[id]?.strength} · {drugMap[id]?.form}</small></span><button className="remove-item" onClick={() => toggle(id)}><X size={15} /></button></div>)}</div>}
    </section>
    <section className="surface decision-panel"><div className="section-title"><div><span className="eyebrow">Safety gate</span><h2>Dispense review</h2></div><ShieldCheck size={20} className="teal-icon" /></div><div className="rule-line" /><label className="field-label">Prescription reference <span>optional unless required</span></label><input className="field" value={prescription} onChange={(e) => setPrescription(e.target.value)} placeholder="Enter reference number" /><label className="field-label">Override reason <span>required for a major interaction</span></label><textarea className="field textarea" value={override} onChange={(e) => setOverride(e.target.value)} placeholder="Only complete this when a pharmacist has reviewed the alert" />
      <button className="primary-button full-button dispense-button" disabled={!selected.length || busy} onClick={() => onDispense({ drug_ids: selected, prescription_reference: prescription || null, override_reason: override || null })}><ClipboardCheck size={18} />{busy ? "Checking cart…" : "Dispense"}</button>
      {!result && <div className="decision-empty"><ShieldCheck size={27} /><strong>Ready for a complete cart review</strong><span>Choose two or more medicines to see DDInteractions and rule outcomes together.</span></div>}
      {result && <div className="result-wrap"><div className={`decision-banner ${resultTone}`}><div className="decision-symbol">{resultTone === "success" ? <CheckCircle2 size={24} /> : resultTone === "warning" ? <AlertTriangle size={24} /> : <XCircle size={24} />}</div><div><span>Decision</span><strong>{result.decision === "OK" ? "Safe to continue" : result.decision === "INFO" ? "Continue with information" : result.decision === "WARN" ? "Pharmacist review" : result.decision === "STOP_OVERRIDDEN" ? "Override recorded" : "Dispense blocked"}</strong><small>{result.decision} · audit #{result.audit_id}</small></div></div><div className="result-section"><h3>Why this decision?</h3>{result.reasons?.length ? result.reasons.map((reason, index) => <div className={`reason-card ${["prescription_required", "major_interaction", "no_unexpired_stock"].includes(reason.code) ? "critical" : ""}`} key={`${reason.code}-${index}`}><AlertCircle size={16} /><span><strong>{reason.code.replaceAll("_", " ")}</strong>{reason.message}</span></div>) : <div className="clean-result"><CheckCircle2 size={16} /> No rule triggered an alert for this cart.</div>}</div>{result.interactions?.length > 0 && <div className="result-section"><h3>DDInteraction review</h3>{result.interactions.map((item, index) => <div className="interaction-card" key={`${item.drug_a_id}-${item.drug_b_id}-${index}`}><div className="interaction-pair"><span>{drugMap[item.drug_a_id]?.generic_name || item.drug_a_id}</span><span>+</span><span>{drugMap[item.drug_b_id]?.generic_name || item.drug_b_id}</span></div><Badge tone={riskTone(item.severity)}>{item.severity}</Badge><small>{item.source || "DDInter development mapping"}</small></div>)}</div>}{result.fefo_picks && Object.keys(result.fefo_picks).length > 0 && <div className="result-section"><h3>FEFO pick recommendation</h3>{Object.entries(result.fefo_picks).map(([id, pick]) => <div className="fefo-row" key={id}><span><strong>{drugMap[id]?.generic_name || id}</strong><small>Batch {pick.batch_no || pick.batch_id}</small></span><span><strong>{number(pick.qty_on_hand)} units</strong><small>Expires {dateLabel(pick.expiry_date)}</small></span></div>)}</div>}{result.can_confirm && <button className="secondary-button full-button" onClick={() => onComplete({ drug_ids: selected, prescription_reference: prescription || null, override_reason: override || null })}><Check size={17} /> Complete dispense</button>}</div>}
    </section>
  </div>;
}

function Inventory({ expiry, velocity }) {
  const [tab, setTab] = useState("expiry");
  const [statuses, setStatuses] = useState(["Expired", "Critical", "Watch"]);
  const filtered = expiry.filter((row) => statuses.includes(row.expiry_status));
  return <><div className="subnav-tabs"><button className={tab === "expiry" ? "active" : ""} onClick={() => setTab("expiry")}><Clock3 size={16} /> Expiry & FEFO</button><button className={tab === "velocity" ? "active" : ""} onClick={() => setTab("velocity")}><Activity size={16} /> Demand velocity</button></div>{tab === "expiry" ? <><div className="metric-grid three"><MetricCard icon={XCircle} label="Expired batches" value={number(expiry.filter((x) => x.expiry_status === "Expired").length)} detail="Never offer for dispensing" tone="coral" /><MetricCard icon={Clock3} label="Critical batches" value={number(expiry.filter((x) => x.expiry_status === "Critical").length)} detail="Expiring within 30 days" tone="amber" /><MetricCard icon={AlertTriangle} label="Units at risk" value={number(expiry.reduce((sum, x) => sum + Number(x.units_at_risk || 0), 0))} detail="Expected not to sell in time" tone="violet" /></div><section className="surface table-surface"><div className="section-title"><div><span className="eyebrow">Inventory control</span><h2>Expiry watchlist</h2></div><div className="filter-pills">{["Expired", "Critical", "Watch", "OK"].map((status) => <button className={statuses.includes(status) ? "active" : ""} key={status} onClick={() => setStatuses((current) => current.includes(status) ? current.filter((x) => x !== status) : [...current, status])}>{status}</button>)}</div></div><div className="data-table"><div className="table-head"><span>Medicine</span><span>Batch</span><span>Units</span><span>Expiry</span><span>Status</span><span>At risk</span></div>{filtered.map((row) => <div className="table-row" key={row.batch_id}><strong>{row.generic_name}</strong><span>{row.batch_no}</span><span>{number(row.qty_on_hand)}</span><span>{dateLabel(row.expiry_date)}</span><Badge tone={riskTone(row.expiry_status)}>{row.expiry_status}</Badge><strong>{number(row.units_at_risk)}</strong></div>)}</div></section></> : <section className="surface table-surface"><div className="section-title"><div><span className="eyebrow">Movement signals</span><h2>Medicine velocity</h2></div><Badge tone="neutral">{velocity.length} tracked</Badge></div><div className="data-table"><div className="table-head"><span>Medicine</span><span>Group</span><span>28-day velocity</span><span>90-day velocity</span><span>Class</span><span>Trend</span></div>{velocity.map((row) => <div className="table-row" key={row.drug_id}><strong>{row.generic_name}</strong><span>{row.atc_level4 || "—"}</span><span>{row.units_per_day_28d}</span><span>{row.units_per_day_90d}</span><Badge tone={row.velocity === "Fast" ? "success" : "neutral"}>{row.velocity}</Badge><span className={row.trend === "Rising" ? "trend-up" : row.trend === "Falling" ? "trend-down" : ""}>{row.trend}</span></div>)}</div></section>}</>;
}

function Forecasting({ products, recommendations }) {
  const [code, setCode] = useState(products[0]?.code || "");
  const [forecast, setForecast] = useState(null);
  const [history, setHistory] = useState([]);
  const [scenario, setScenario] = useState(null);
  const [demandMultiplier, setDemandMultiplier] = useState(1);
  const [leadTime, setLeadTime] = useState(7);
  const selectedRecommendation = recommendations.find((item) => item.product_group === code);
  useEffect(() => { if (!code) return; Promise.all([request(`/forecast/${code}`), request(`/products/${code}/history?days=90`), request(`/reorder/${code}`)]).then(([f, h, r]) => { setForecast({ ...f, recommendation: r }); setHistory(h); setLeadTime(r.lead_time_days); setScenario(null); }).catch(() => {}); }, [code]);
  const runScenario = async () => { if (!forecast) return; setScenario(await request(`/reorder/${code}/what-if?usable_stock=${forecast.recommendation.usable_stock}&demand_multiplier=${demandMultiplier}&lead_time_days=${leadTime}`)); };
  const chartData = [...history.slice(-30).map((x) => Number(x.quantity)), ...(forecast?.forecasts || []).map((x) => Number(x.predicted_quantity))];
  const max = Math.max(...chartData, 1);
  return <><section className="surface planning-header"><div><span className="eyebrow">Demand planning</span><h2>Forecast with an action attached</h2><p>Select a product group to see history, forecast, and replenishment pressure in one view.</p></div><select className="select-control" value={code} onChange={(e) => setCode(e.target.value)}>{products.map((item) => <option key={item.code} value={item.code}>{item.code} · {item.description}</option>)}</select></section>{forecast && <><div className="metric-grid four"><MetricCard icon={TriangleAlert} label="Risk level" value={forecast.recommendation.risk_level} detail="Current planning signal" tone={riskTone(forecast.recommendation.risk_level) === "danger" ? "coral" : "amber"} /><MetricCard icon={Boxes} label="Usable stock" value={number(forecast.recommendation.usable_stock)} detail="Unexpired units" tone="teal" /><MetricCard icon={Clock3} label="Days cover" value={forecast.recommendation.days_of_cover ?? "∞"} detail="At forecast demand" tone="violet" /><MetricCard icon={Truck} label="Suggested order" value={number(forecast.recommendation.reorder_quantity)} detail="Pack-rounded quantity" tone="coral" /></div><div className="content-grid planning-grid"><section className="surface chart-panel"><div className="section-title"><div><span className="eyebrow">Demand trajectory</span><h2>{code} forecast</h2></div><Badge tone="neutral">{forecast.forecast_method}</Badge></div><div className="chart"><div className="chart-bars">{chartData.map((value, index) => <div className={`chart-bar ${index >= chartData.length - 7 ? "forecast-bar" : ""}`} key={`${value}-${index}`} style={{ height: `${Math.max(5, (value / max) * 100)}%` }} title={`${value.toFixed(1)} units`} />)}</div><div className="chart-axis"><span>30 days history</span><span>7 day forecast →</span></div></div></section><section className="surface whatif-panel"><div className="section-title"><div><span className="eyebrow">Planning sandbox</span><h2>What if?</h2></div><SlidersHorizontal size={19} className="teal-icon" /></div><p className="section-intro">Change assumptions and see the recommended order move.</p><label className="range-label"><span>Demand multiplier</span><strong>{demandMultiplier.toFixed(1)}×</strong></label><input type="range" min="0.5" max="2" step="0.1" value={demandMultiplier} onChange={(e) => setDemandMultiplier(Number(e.target.value))} /><label className="range-label"><span>Supplier lead time</span><strong>{leadTime} days</strong></label><input type="range" min="1" max="30" step="1" value={leadTime} onChange={(e) => setLeadTime(Number(e.target.value))} /><button className="primary-button full-button" onClick={runScenario}><SlidersHorizontal size={17} /> Recalculate plan</button>{scenario && <div className="scenario-result"><span>Scenario reorder</span><strong>{number(scenario.reorder_quantity)} units</strong><small>{scenario.risk_level} risk · {scenario.days_of_cover ?? "∞"} days cover</small></div>}</section></div></>}{selectedRecommendation && <section className="surface table-surface"><div className="section-title"><div><span className="eyebrow">All groups</span><h2>Portfolio planning view</h2></div></div><RecommendationsTable rows={recommendations} /></section>}</>;
}

function Assistant() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const examples = ["What does the dispensing guideline say about dispensing medicines?", "What does EMHSLU say about amoxicillin?", "What is the purpose of the Uganda Clinical Guidelines?"];
  const ask = async (value = question) => { if (!value.trim()) return; setBusy(true); try { setAnswer(await request("/ask", { method: "POST", body: JSON.stringify({ question: value }) })); } finally { setBusy(false); } };
  return <section className="assistant-layout"><div className="assistant-intro"><div className="assistant-orb"><Sparkles size={28} /></div><span className="eyebrow">Cited reference library</span><h2>Ask the pharmacy guidance.</h2><p>Search the Uganda Clinical Guidelines, EMHSLU, WHO Essential Medicines List, and the dispensing guideline. Answers show the source pages used.</p><div className="example-list">{examples.map((example) => <button key={example} onClick={() => { setQuestion(example); ask(example); }}>{example}<ArrowUpRight size={15} /></button>)}</div></div><section className="surface assistant-card"><div className="search-box large"><Search size={18} /><input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} placeholder="Ask about dispensing, procurement, medicines, or stock…" /><button className="primary-button" onClick={() => ask()} disabled={busy}>{busy ? "Searching…" : "Ask"}</button></div>{!answer && <EmptyState icon={BookOpen} title="Your cited answer will appear here" detail="Ask a specific question to search the local reference library." />}{answer && <div className="answer-content">{answer.found ? <><div className="answer-copy"><div className="answer-label"><CheckCircle2 size={15} /> Extractive answer</div><p>{answer.answer}</p></div><div className="citation-list"><h3>Sources used</h3>{answer.citations.map((citation, index) => <div className="citation" key={`${citation.doc_name}-${citation.page}-${index}`}><BookOpen size={16} /><span><strong>{citation.doc_name}</strong><small>Page {citation.page} · {citation.section}</small></span><ChevronRight size={15} /></div>)}</div></> : <div className="not-found"><Search size={23} /><strong>{answer.refused ? "That request is outside the reference boundary." : "Nothing found in the reference library."}</strong><span>{answer.answer}</span></div>}</div>}</section></section>;
}

function Catalogue({ drugs, onAdded }) {
  const [form, setForm] = useState({ generic_name: "", strength: "", form: "tablet", atc_code: "", atc_level4: "", pack_size: 10, lead_time_days: 7, initial_stock: 100, expiry_date: "", prescription_required: false, source_ref: "" });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const filtered = drugs.filter((d) => `${d.generic_name} ${d.drug_id}`.toLowerCase().includes(query.toLowerCase()));
  const change = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => { event.preventDefault(); setStatus("saving"); try { await request("/inventory/medications", { method: "POST", body: JSON.stringify({ ...form, pack_size: Number(form.pack_size), lead_time_days: Number(form.lead_time_days), initial_stock: Number(form.initial_stock), expiry_date: form.expiry_date || null, source_name: form.prescription_required ? "User-entered catalogue rule" : null, source_ref: form.source_ref || null }) }); setStatus("saved"); onAdded(); setForm((current) => ({ ...current, generic_name: "", strength: "", atc_code: "", atc_level4: "", source_ref: "" })); } catch (error) { setStatus(error.message); } };
  return <><section className="surface catalogue-form"><div className="section-title"><div><span className="eyebrow">Catalogue management</span><h2>Add a medicine</h2></div><PackageCheck size={20} className="teal-icon" /></div><p className="section-intro">Extend the working catalogue without touching source files. New medicines become available to the dispensing cart immediately.</p><form onSubmit={submit} className="form-grid"><label>Generic name *<input required value={form.generic_name} onChange={(e) => change("generic_name", e.target.value)} placeholder="e.g. Ceftriaxone" /></label><label>Strength<input value={form.strength} onChange={(e) => change("strength", e.target.value)} placeholder="e.g. 1 g" /></label><label>Dosage form<select value={form.form} onChange={(e) => change("form", e.target.value)}>{["tablet", "capsule", "injection", "cream", "syrup", "inhaler", "infusion", "other"].map((x) => <option key={x}>{x}</option>)}</select></label><label>ATC code<input value={form.atc_code} onChange={(e) => change("atc_code", e.target.value)} placeholder="Optional" /></label><label>ATC level 4<input value={form.atc_level4} onChange={(e) => change("atc_level4", e.target.value)} placeholder="Optional" /></label><label>Pack size<input type="number" min="1" value={form.pack_size} onChange={(e) => change("pack_size", e.target.value)} /></label><label>Lead time (days)<input type="number" min="0" value={form.lead_time_days} onChange={(e) => change("lead_time_days", e.target.value)} /></label><label>Opening stock<input type="number" min="0" value={form.initial_stock} onChange={(e) => change("initial_stock", e.target.value)} /></label><label>Opening batch expiry<input type="date" value={form.expiry_date} onChange={(e) => change("expiry_date", e.target.value)} /></label><label className="checkbox-field"><input type="checkbox" checked={form.prescription_required} onChange={(e) => change("prescription_required", e.target.checked)} /> Prescription reference required</label>{form.prescription_required && <label>Rule source/reference<input value={form.source_ref} onChange={(e) => change("source_ref", e.target.value)} placeholder="Required to enforce the gate" /></label>}<div className="form-actions"><button className="primary-button" disabled={status === "saving"}>{status === "saving" ? "Saving…" : "Add medicine"}</button>{status === "saved" && <span className="saved-message"><CheckCircle2 size={16} /> Medicine added</span>}{status && !["saving", "saved"].includes(status) && <span className="error-message">{status}</span>}</div></form></section><section className="surface table-surface"><div className="section-title"><div><span className="eyebrow">Medicine library</span><h2>{drugs.length} medicines available</h2></div><div className="search-box compact"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter catalogue" /></div></div><div className="data-table"><div className="table-head"><span>Medicine</span><span>Strength</span><span>Form</span><span>ATC group</span><span>Lead time</span><span /></div>{filtered.map((drug) => <div className="table-row" key={drug.drug_id}><strong>{drug.generic_name}</strong><span>{drug.strength || "—"}</span><span>{drug.form || "—"}</span><span>{drug.atc_level4 || "—"}</span><span>{drug.lead_time_days} days</span><ChevronRight size={16} className="row-chevron" /></div>)}</div></section></>;
}

export default function App() {
  const [page, setPage] = useState("overview");
  const [data, setData] = useState({ health: null, products: [], drugs: [], recommendations: [], expiry: [], velocity: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkResult, setCheckResult] = useState(null);
  const [checkPayload, setCheckPayload] = useState(null);
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { const [health, products, drugs, recommendations, expiry, velocity] = await Promise.all([request("/health"), request("/products"), request("/inventory/drugs"), request("/recommendations"), request("/inventory/expiry"), request("/inventory/velocity")]); setData({ health, products, drugs, recommendations, expiry, velocity }); } catch (e) { setError(e.message); } finally { setLoading(false); } }, []);
  useEffect(() => { load(); }, [load]);
  const dispense = async (payload) => { setBusy(true); setCheckPayload(payload); try { setCheckResult(await request("/dispense/check", { method: "POST", body: JSON.stringify(payload) })); } catch (e) { setError(e.message); } finally { setBusy(false); } };
  const complete = async (payload) => { setBusy(true); try { setCheckResult(await request("/dispense/confirm", { method: "POST", body: JSON.stringify(payload) })); } catch (e) { setError(e.message); } finally { setBusy(false); } };
  const launchScenario = async (type) => { setScenario(type); if (type === "prescription") { setPage("dispensing"); await dispense({ drug_ids: ["D029"], prescription_reference: null, override_reason: null }); } else if (type === "interaction") { setPage("dispensing"); await dispense({ drug_ids: ["D047", "D005"], prescription_reference: null, override_reason: null }); } else if (type === "stockout") setPage("forecasting"); else setPage("inventory"); };
  const added = async () => { await load(); setPage("catalogue"); };
  const pageMeta = { overview: ["Pharmacy command center", "A focused view of stock health, demand, and the next safe action."], dispensing: ["Dispensing console", "Review the complete medicine cart before a dispense is completed."], inventory: ["Inventory control", "See expiry pressure, FEFO priorities, and medicine movement."], forecasting: ["Demand planning", "Translate demand signals into a practical replenishment decision."], catalogue: ["Medicine catalogue", "Manage the medicines your team can select, review, and dispense."], assistant: ["Reference assistant", "Ask the pharmacy guidance and see exactly where the answer came from."] };
  if (error && !data.health) return <div className="app-error"><LogoMark /><XCircle size={36} /><h1>API connection unavailable</h1><p>{error}</p><code>uvicorn api.main:app --reload</code><button className="primary-button" onClick={load}>Try again</button></div>;
  return <div className="app-shell"><Sidebar page={page} setPage={setPage} health={data.health} /><main className="main-content"><Topbar title={pageMeta[page][0]} subtitle={pageMeta[page][1]} onRefresh={load} loading={loading} />{error && <div className="toast-error"><AlertCircle size={17} />{error}<button onClick={() => setError("")}><X size={15} /></button></div>}{loading && !data.drugs.length ? <div className="loading-state"><div className="loader" /><span>Loading pharmacy workspace…</span></div> : <div className="page-content">{page === "overview" && <Overview data={data} onPage={setPage} onScenario={launchScenario} />}{page === "dispensing" && <Dispensing drugs={data.drugs} result={checkResult} onDispense={dispense} onComplete={complete} busy={busy} />}{page === "inventory" && <Inventory expiry={data.expiry} velocity={data.velocity} />}{page === "forecasting" && <Forecasting products={data.products} recommendations={data.recommendations} />}{page === "catalogue" && <Catalogue drugs={data.drugs} onAdded={added} />}{page === "assistant" && <Assistant />}</div>}</main></div>;
}
