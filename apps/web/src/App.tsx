import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  ChevronRight,
  CircleDollarSign,
  Crosshair,
  Database,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  LineChart,
  ListFilter,
  Menu,
  Moon,
  MoreHorizontal,
  PanelLeftClose,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  WalletCards,
  X,
  Zap,
} from "lucide-react";

type View = "overview" | "screener" | "rrg" | "backtest" | "options" | "arbitrage" | "research" | "settings";
type Operator = ">" | "<" | ">=" | "<=" | "=";

type Condition = {
  id: string;
  field: string;
  operator: Operator;
  value: number;
  timeframe: string;
};

type Quote = {
  symbol: string;
  exchange: string;
  sector: string;
  ltp: number;
  changePct: number;
  volume: number;
  signal: string;
  score: number;
};

type RrgPoint = {
  symbol: string;
  sector: string;
  rsRatio: number;
  rsMomentum: number;
  quadrant: "leading" | "weakening" | "lagging" | "improving";
};

type ResearchReport = {
  report_id: string;
  symbol: string;
  mode: string;
  data_quality: string;
  as_of: string;
  decision: string;
  confidence: number;
  summary: string;
  findings: Array<{ role: string; title: string; conclusion: string; confidence: number }>;
  evidence: Array<{ id: string; role: string; status: string; summary: string }>;
  risks: string[];
  next_actions: string[];
  agent_trace: string[];
  approval_required: boolean;
  order_authority: "none";
  warnings: string[];
};

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const navItems: Array<{ id: View; label: string; icon: LucideIcon }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "screener", label: "Screener", icon: ListFilter },
  { id: "rrg", label: "RRG Radar", icon: Crosshair },
  { id: "backtest", label: "Backtest Lab", icon: FlaskConical },
  { id: "options", label: "Option Chain", icon: BarChart3 },
  { id: "arbitrage", label: "Arbitrage", icon: Zap },
];

const demoQuotes: Quote[] = [
  { symbol: "RELIANCE", exchange: "NSE", sector: "Energy", ltp: 2942.4, changePct: 1.84, volume: 8420000, signal: "Momentum", score: 86 },
  { symbol: "ICICIBANK", exchange: "NSE", sector: "Banks", ltp: 1328.65, changePct: 1.25, volume: 6110000, signal: "Momentum", score: 82 },
  { symbol: "BHARTIARTL", exchange: "NSE", sector: "Telecom", ltp: 1845.1, changePct: 0.94, volume: 4340000, signal: "Watch", score: 78 },
  { symbol: "TCS", exchange: "NSE", sector: "IT", ltp: 4120.75, changePct: -0.22, volume: 2120000, signal: "Watch", score: 57 },
  { symbol: "HDFCBANK", exchange: "NSE", sector: "Banks", ltp: 1764.2, changePct: 0.41, volume: 5880000, signal: "Watch", score: 71 },
  { symbol: "SUNPHARMA", exchange: "NSE", sector: "Pharma", ltp: 1742.3, changePct: 2.32, volume: 3020000, signal: "Momentum", score: 89 },
  { symbol: "INFY", exchange: "NSE", sector: "IT", ltp: 1936.55, changePct: -0.74, volume: 3510000, signal: "Watch", score: 46 },
  { symbol: "AXISBANK", exchange: "NSE", sector: "Banks", ltp: 1215.8, changePct: 0.86, volume: 4790000, signal: "Momentum", score: 76 },
];

const demoRrg: RrgPoint[] = [
  { symbol: "RELIANCE", sector: "Energy", rsRatio: 102.6, rsMomentum: 103.4, quadrant: "leading" },
  { symbol: "ICICIBANK", sector: "Banks", rsRatio: 101.8, rsMomentum: 102.2, quadrant: "leading" },
  { symbol: "SUNPHARMA", sector: "Pharma", rsRatio: 103.5, rsMomentum: 100.9, quadrant: "leading" },
  { symbol: "BHARTIARTL", sector: "Telecom", rsRatio: 99.4, rsMomentum: 101.3, quadrant: "improving" },
  { symbol: "TCS", sector: "IT", rsRatio: 98.7, rsMomentum: 99.1, quadrant: "lagging" },
  { symbol: "INFY", sector: "IT", rsRatio: 97.8, rsMomentum: 98.4, quadrant: "lagging" },
  { symbol: "AXISBANK", sector: "Banks", rsRatio: 100.6, rsMomentum: 99.2, quadrant: "weakening" },
];

const defaultConditions: Condition[] = [
  { id: "rsi", field: "rsi", operator: ">", value: 50, timeframe: "1d" },
  { id: "change", field: "changePct", operator: ">", value: 0, timeframe: "1d" },
  { id: "volume", field: "volume", operator: ">", value: 1000000, timeframe: "1d" },
];

const optionRows = [
  { strike: 24100, callLtp: 438, callOi: 31600, callChangeOi: 4200, putLtp: 88, putOi: 74800, putChangeOi: 9200, iv: 15.2 },
  { strike: 24200, callLtp: 366, callOi: 45100, callChangeOi: 6100, putLtp: 111, putOi: 68000, putChangeOi: 7600, iv: 14.4 },
  { strike: 24300, callLtp: 298, callOi: 58200, callChangeOi: 8400, putLtp: 145, putOi: 59700, putChangeOi: 5300, iv: 13.6 },
  { strike: 24400, callLtp: 236, callOi: 71400, callChangeOi: 10100, putLtp: 189, putOi: 51200, putChangeOi: 3800, iv: 12.9 },
  { strike: 24500, callLtp: 178, callOi: 84000, callChangeOi: 12600, putLtp: 232, putOi: 44800, putChangeOi: 2200, iv: 12.8 },
  { strike: 24600, callLtp: 132, callOi: 93200, callChangeOi: 14300, putLtp: 294, putOi: 37900, putChangeOi: -1800, iv: 13.1 },
  { strike: 24700, callLtp: 94, callOi: 106000, callChangeOi: 16900, putLtp: 361, putOi: 31100, putChangeOi: -4200, iv: 13.8 },
];

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCompact(value: number): string {
  if (value >= 10000000) return (value / 10000000).toFixed(1) + "Cr";
  if (value >= 100000) return (value / 100000).toFixed(1) + "L";
  if (value >= 1000) return (value / 1000).toFixed(1) + "K";
  return String(value);
}

function App() {
  const [view, setView] = useState<View>("overview");
  const [mobileNav, setMobileNav] = useState(false);
  const [universe, setUniverse] = useState("nifty50");
  const [timeframe, setTimeframe] = useState("1d");
  const [conditions, setConditions] = useState<Condition[]>(defaultConditions);
  const [scanResults, setScanResults] = useState<Quote[]>(demoQuotes);
  const [apiMode, setApiMode] = useState("Demo data");
  const [notice, setNotice] = useState("Paper mode is active. Connect a rotated SmartAPI key in the backend to load your own market data.");

  useEffect(() => {
    fetch(API_URL + "/api/v1/status")
      .then((response) => response.json())
      .then((data) => {
        if (data.appMode === "connected") setApiMode("SmartAPI connected");
      })
      .catch(() => setApiMode("Demo data"));
  }, []);

  function updateCondition(id: string, patch: Partial<Condition>) {
    setConditions((current) => current.map((condition) => (
      condition.id === id ? { ...condition, ...patch } : condition
    )));
  }

  function addCondition() {
    setConditions((current) => [
      ...current,
      { id: "condition-" + String(Date.now()), field: "changePct", operator: ">", value: 0, timeframe },
    ]);
  }

  function removeCondition(id: string) {
    setConditions((current) => current.filter((condition) => condition.id !== id));
  }

  async function runScan() {
    setNotice("Running scan with the current conditions...");
    try {
      const response = await fetch(API_URL + "/api/v1/screener/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ universe, timeframe, conditions, limit: 50 }),
      });
      if (!response.ok) throw new Error("API unavailable");
      const data = await response.json();
      setScanResults(data.results || demoQuotes);
      setApiMode(data.mode === "connected" ? "SmartAPI connected" : "Demo data");
      setNotice(data.warning || "Scan completed.");
      setView("screener");
    } catch {
      setScanResults(demoQuotes);
      setNotice("The API is not running, so the interface is showing safe demo results.");
      setView("screener");
    }
  }

  function selectView(nextView: View) {
    setView(nextView);
    setMobileNav(false);
  }

  return (
    <div className="app-shell">
      <aside className={mobileNav ? "sidebar sidebar-open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark"><Activity size={20} /></div>
          <div>
            <strong>ALL IN ONE</strong>
            <span>TRADING LAB</span>
          </div>
        </div>

        <div className="mode-pill">
          <span className="pulse-dot" />
          <span>{apiMode}</span>
          <ShieldCheck size={14} />
        </div>

        <nav className="nav-list">
          <div className="nav-caption">WORKSPACE</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={view === item.id ? "nav-item nav-item-active" : "nav-item"}
                onClick={() => selectView(item.id)}
              >
                <Icon size={17} />
                <span>{item.label}</span>
                {item.id === "screener" && <span className="nav-count">3</span>}
              </button>
            );
          })}

          <div className="nav-caption nav-caption-space">TOOLS</div>
          <button className="nav-item" onClick={() => { setNotice("Research Copilot is advisory-only and cannot place orders."); selectView("research"); }}>
            <Bot size={17} />
            <span>Research Copilot</span>
            <span className="beta-tag">BETA</span>
          </button>
          <button className="nav-item" onClick={() => setNotice("Your trade journal will be attached to the paper-trading ledger.")}>
            <BookOpen size={17} />
            <span>Trade Journal</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => selectView("settings")}>
            <Settings size={17} />
            <span>Settings</span>
          </button>
          <div className="user-mini">
            <div className="avatar">R</div>
            <div>
              <strong>Private workspace</strong>
              <span>Single user</span>
            </div>
            <MoreHorizontal size={16} />
          </div>
        </div>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div className="mobile-brand">
            <button className="icon-button mobile-menu" onClick={() => setMobileNav(!mobileNav)}><Menu size={19} /></button>
            <div className="brand-mark"><Activity size={18} /></div>
            <strong>ALL IN ONE</strong>
          </div>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{navItems.find((item) => item.id === view)?.label || (view === "research" ? "Research Copilot" : "Settings")}</strong>
          </div>
          <div className="top-actions">
            <div className="market-state"><span className="live-dot" /> Market closed</div>
            <button className="icon-button"><Bell size={17} /></button>
            <button className="icon-button"><Moon size={17} /></button>
            <div className="top-avatar">R</div>
          </div>
        </header>

        <div className="content">
          <div className="notice-banner">
            <div className="notice-icon"><ShieldCheck size={17} /></div>
            <span>{notice}</span>
            <button onClick={() => setNotice("")}><X size={15} /></button>
          </div>

          {view === "overview" && <Overview onNavigate={selectView} onRunScan={runScan} />}
          {view === "screener" && (
            <Screener
              universe={universe}
              timeframe={timeframe}
              conditions={conditions}
              results={scanResults}
              onUniverse={setUniverse}
              onTimeframe={setTimeframe}
              onUpdateCondition={updateCondition}
              onAddCondition={addCondition}
              onRemoveCondition={removeCondition}
              onRunScan={runScan}
            />
          )}
          {view === "rrg" && <RrgView timeframe={timeframe} onTimeframe={setTimeframe} />}
          {view === "backtest" && <BacktestView />}
          {view === "options" && <OptionsView />}
          {view === "arbitrage" && <ArbitrageView />}
          {view === "research" && <ResearchView />}
          {view === "settings" && <SettingsView />}
        </div>
      </main>
    </div>
  );
}

function Overview({ onNavigate, onRunScan }: { onNavigate: (view: View) => void; onRunScan: () => void }) {
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">FRIDAY, 28 AUGUST 2026</div>
          <h1>Good morning, Rahul<span className="accent">.</span></h1>
          <p>Your private market workspace is ready for research.</p>
        </div>
        <button className="primary-button" onClick={onRunScan}><Play size={15} /> Run saved scan</button>
      </div>

      <section className="metric-grid">
        <MetricCard label="Paper portfolio" value="₹1,00,000" sub="Available capital" icon={WalletCards} tint="blue" />
        <MetricCard label="Today’s move" value="+₹2,480" sub="+1.84% simulated" icon={TrendingUp} tint="green" positive />
        <MetricCard label="Open positions" value="04" sub="2 momentum · 2 watch" icon={Target} tint="purple" />
        <MetricCard label="Risk budget" value="₹18,500" sub="18.5% of capital" icon={Gauge} tint="orange" />
      </section>

      <div className="section-heading">
        <div>
          <h2>Market cockpit</h2>
          <p>One view for signals, relative strength and execution planning.</p>
        </div>
        <button className="text-button" onClick={() => onNavigate("settings")}>Configure workspace <ChevronRight size={15} /></button>
      </div>

      <section className="cockpit-grid">
        <div className="panel chart-panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">NIFTY 50 · 1D</span>
              <h3>Market pulse</h3>
            </div>
            <div className="chart-value"><strong>24,548.70</strong><span className="positive-text">+0.84%</span></div>
          </div>
          <MiniChart />
          <div className="chart-footer">
            <span><i className="legend-dot blue" /> Price</span>
            <span><i className="legend-dot violet" /> EMA 21</span>
            <span className="muted">Last update: demo feed</span>
          </div>
        </div>
        <div className="panel signal-panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">SAVED WORKFLOW</span>
              <h3>Momentum scan</h3>
            </div>
            <button className="icon-button"><MoreHorizontal size={17} /></button>
          </div>
          <div className="signal-summary">
            <div className="signal-number">08</div>
            <div><strong>symbols matched</strong><span>RSI &gt; 50 · Change &gt; 0%</span></div>
          </div>
          <div className="mini-list">
            {demoQuotes.slice(0, 4).map((quote) => (
              <div className="mini-row" key={quote.symbol}>
                <div className="symbol-chip">{quote.symbol.slice(0, 2)}</div>
                <strong>{quote.symbol}</strong>
                <span className={quote.changePct >= 0 ? "positive-text" : "negative-text"}>{quote.changePct >= 0 ? "+" : ""}{quote.changePct.toFixed(2)}%</span>
              </div>
            ))}
          </div>
          <button className="secondary-button full-button" onClick={() => onNavigate("screener")}>Open screener <ArrowUpRight size={15} /></button>
        </div>
      </section>

      <section className="lower-grid">
        <div className="panel">
          <div className="panel-header">
            <div><span className="panel-kicker">RELATIVE ROTATION</span><h3>RRG radar</h3></div>
            <button className="text-button" onClick={() => onNavigate("rrg")}>Open radar <ArrowUpRight size={15} /></button>
          </div>
          <RrgMini />
        </div>
        <div className="panel">
          <div className="panel-header">
            <div><span className="panel-kicker">RESEARCH QUEUE</span><h3>Next actions</h3></div>
            <Sparkles size={17} className="violet-icon" />
          </div>
          <div className="action-list">
            <ActionItem icon={ListFilter} title="Review today’s scan" detail="8 symbols matched your saved rules" onClick={() => onNavigate("screener")} />
            <ActionItem icon={FlaskConical} title="Validate EMA strategy" detail="Run a walk-forward preview" onClick={() => onNavigate("backtest")} />
            <ActionItem icon={CircleDollarSign} title="Inspect option chain" detail="NIFTY nearest expiry is ready" onClick={() => onNavigate("options")} />
          </div>
        </div>
      </section>
    </>
  );
}

function MetricCard({ label, value, sub, icon: Icon, tint, positive }: { label: string; value: string; sub: string; icon: LucideIcon; tint: string; positive?: boolean }) {
  return (
    <div className="metric-card">
      <div className={"metric-icon " + tint}><Icon size={18} /></div>
      <div className="metric-copy"><span>{label}</span><strong className={positive ? "positive-text" : ""}>{value}</strong><small>{sub}</small></div>
      <ArrowUpRight size={15} className="metric-arrow" />
    </div>
  );
}

function MiniChart() {
  return (
    <div className="mini-chart-wrap">
      <svg viewBox="0 0 720 220" role="img" aria-label="Demo market pulse chart">
        <defs>
          <linearGradient id="area-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#4da3ff" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#4da3ff" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d="M0 180 C60 165 72 175 115 135 S185 150 225 115 S285 95 320 125 S380 95 420 105 S480 50 525 74 S590 30 625 54 S680 42 720 22 L720 220 L0 220 Z" fill="url(#area-fill)" />
        <path d="M0 180 C60 165 72 175 115 135 S185 150 225 115 S285 95 320 125 S380 95 420 105 S480 50 525 74 S590 30 625 54 S680 42 720 22" fill="none" stroke="#4da3ff" strokeWidth="3" />
        <path d="M0 194 C70 178 86 184 125 160 S185 165 230 142 S290 118 330 139 S390 121 430 124 S480 90 530 96 S590 70 630 82 S680 66 720 52" fill="none" stroke="#8f7cff" strokeWidth="2" strokeDasharray="5 6" opacity="0.8" />
        {[45, 150, 255, 360, 465, 570, 675].map((x) => <line key={x} x1={x} x2={x} y1="14" y2="210" stroke="#1f3048" strokeWidth="1" />)}
        {[45, 95, 145, 195].map((y) => <line key={y} x1="0" x2="720" y1={y} y2={y} stroke="#1f3048" strokeWidth="1" />)}
      </svg>
      <div className="chart-axis"><span>01 Aug</span><span>08 Aug</span><span>15 Aug</span><span>22 Aug</span><span>28 Aug</span></div>
    </div>
  );
}


function ResearchView() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Run the deterministic research packet against the shared API.");
  const [report, setReport] = useState<ResearchReport | null>(null);

  async function analyze() {
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(API_URL + "/api/v1/research/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          timeframe: "1d",
          universe: "nifty50",
          include_news: true,
          include_fundamentals: true,
        }),
      });
      if (!response.ok) throw new Error("Research API unavailable");
      const data = await response.json() as ResearchReport;
      setReport(data);
      setMessage("Research packet updated. Review evidence and risks before creating any paper action.");
    } catch {
      setMessage("Backend unavailable. Start the FastAPI service, then run the analysis again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-heading compact-heading">
        <div>
          <div className="eyebrow">ADVISORY RESEARCH · NO ORDER AUTHORITY</div>
          <h1>Research Copilot<span className="accent">.</span></h1>
          <p>TradingAgents-inspired specialist roles with deterministic evidence and explicit uncertainty.</p>
        </div>
        <div className="heading-actions">
          <div className="search-box"><Search size={15} /><input value={symbol} onChange={(event) => setSymbol(event.currentTarget.value.toUpperCase())} aria-label="Research symbol" /></div>
          <button className="primary-button" onClick={analyze} disabled={loading}>{loading ? <RefreshCw className="spin" size={15} /> : <Sparkles size={15} />}{loading ? "Analyzing..." : "Analyze"}</button>
        </div>
      </div>

      {!report && <div className="panel"><div className="panel-header"><div><span className="panel-kicker">RESEARCH PACKET</span><h3>Evidence-first workflow</h3></div><span className="status-badge purple-badge">Advisory only</span></div><p className="muted">{message}</p><div className="action-list"><ActionItem icon={Database} title="Freeze a market snapshot" detail="Every future report will carry source and as-of metadata." onClick={analyze} /><ActionItem icon={ShieldCheck} title="Require manual approval" detail="Agents cannot place or approve orders." onClick={() => setMessage("Manual approval gate remains enabled for every paper action.")} /></div></div>}
      {report && (
        <div className="settings-grid">
          <div className="panel">
            <div className="panel-header"><div><span className="panel-kicker">{report.mode.toUpperCase()} · {report.data_quality.toUpperCase()}</span><h3>{report.symbol} · {report.decision.replace("_", " ")}</h3></div><span className="status-badge green-badge">{Math.round(report.confidence * 100)}% confidence</span></div>
            <p>{report.summary}</p>
            <div className="settings-note"><ShieldCheck size={14} /> Manual approval required: {report.approval_required ? "yes" : "no"} · order authority: {report.order_authority}</div>
            <div className="check-list">{report.agent_trace.map((step) => <div className="check-line" key={step}><Sparkles size={14} /><span>{step}</span><span className="muted">logged</span></div>)}</div>
          </div>
          <div className="panel">
            <div className="panel-header"><div><span className="panel-kicker">SPECIALIST FINDINGS</span><h3>What the packet says</h3></div><span className="status-badge orange-badge">{new Date(report.as_of).toLocaleString()}</span></div>
            {report.findings.map((finding) => <div className="action-item" key={finding.role}><div className="action-icon"><Bot size={16} /></div><div><strong>{finding.title}</strong><span>{finding.conclusion}</span></div><span className="muted">{Math.round(finding.confidence * 100)}%</span></div>)}
          </div>
          <div className="panel">
            <div className="panel-header"><div><span className="panel-kicker">EVIDENCE & RISKS</span><h3>What is still missing</h3></div><ShieldCheck className="green-icon" size={20} /></div>
            {report.evidence.map((item) => <div className="check-line" key={item.id}><Database size={14} /><span>{item.role}: {item.summary}</span><span className="muted">{item.status}</span></div>)}
            {report.risks.map((risk) => <div className="settings-note" key={risk}><ShieldCheck size={14} />{risk}</div>)}
            {report.warnings.map((warning) => <div className="warning-card" key={warning}><ShieldCheck size={14} /><span>{warning}</span></div>)}
          </div>
        </div>
      )}
      {report && <div className="panel"><div className="panel-header"><div><span className="panel-kicker">NEXT ACTIONS</span><h3>Safe progression</h3></div><SlidersHorizontal size={18} className="violet-icon" /></div><div className="action-list">{report.next_actions.map((action) => <ActionItem icon={ArrowUpRight} title={action} detail="Queued as a research step; no order is created." onClick={() => setMessage(action)} key={action} />)}</div><p className="muted">{message}</p></div>}
    </>
  );
}

function Screener({ universe, timeframe, conditions, results, onUniverse, onTimeframe, onUpdateCondition, onAddCondition, onRemoveCondition, onRunScan }: {
  universe: string;
  timeframe: string;
  conditions: Condition[];
  results: Quote[];
  onUniverse: (value: string) => void;
  onTimeframe: (value: string) => void;
  onUpdateCondition: (id: string, patch: Partial<Condition>) => void;
  onAddCondition: () => void;
  onRemoveCondition: (id: string) => void;
  onRunScan: () => void;
}) {
  return (
    <>
      <div className="page-heading compact-heading">
        <div><div className="eyebrow">RULE BUILDER</div><h1>Market screener<span className="accent">.</span></h1><p>Compose technical and fundamental conditions like your Chartink workflow.</p></div>
        <div className="heading-actions"><button className="secondary-button"><Bell size={15} /> Save alert</button><button className="primary-button" onClick={onRunScan}><RefreshCw size={15} /> Run scan</button></div>
      </div>
      <div className="screener-layout">
        <div className="panel condition-panel">
          <div className="panel-header"><div><span className="panel-kicker">SCAN DEFINITION</span><h3>Conditions</h3></div><button className="icon-button"><SlidersHorizontal size={17} /></button></div>
          <div className="scan-controls">
            <label>Universe<select value={universe} onChange={(event) => onUniverse(event.currentTarget.value)}><option value="nifty50">NIFTY 50</option><option value="banknifty">BANKNIFTY</option><option value="midcap150">MIDCAP 150</option><option value="custom">Custom list</option><option value="crypto">Crypto research</option></select></label>
            <label>Base timeframe<select value={timeframe} onChange={(event) => onTimeframe(event.currentTarget.value)}><option value="5m">5 minute</option><option value="15m">15 minute</option><option value="1h">1 hour</option><option value="1d">Daily</option><option value="1w">Weekly</option><option value="1M">Monthly</option></select></label>
          </div>
          <div className="logic-row"><span className="logic-label">Match</span><button className="logic-button active">ALL</button><button className="logic-button">ANY</button><span className="muted">conditions</span></div>
          <div className="condition-list">
            {conditions.map((condition, index) => (
              <div className="condition-row" key={condition.id}>
                <span className="condition-index">{String(index + 1).padStart(2, "0")}</span>
                <select value={condition.field} onChange={(event) => onUpdateCondition(condition.id, { field: event.currentTarget.value })}><option value="rsi">RSI (14)</option><option value="changePct">Change %</option><option value="volume">Volume</option><option value="ltp">Last price</option><option value="score">Momentum score</option></select>
                <select className="operator-select" value={condition.operator} onChange={(event) => onUpdateCondition(condition.id, { operator: event.currentTarget.value as Operator })}><option value=">">&gt;</option><option value="<">&lt;</option><option value=">=">&gt;=</option><option value="<=">&lt;=</option><option value="=">=</option></select>
                <input type="number" value={condition.value} onChange={(event) => onUpdateCondition(condition.id, { value: Number(event.currentTarget.value) })} />
                <select className="timeframe-select" value={condition.timeframe} onChange={(event) => onUpdateCondition(condition.id, { timeframe: event.currentTarget.value })}><option value="5m">5m</option><option value="15m">15m</option><option value="1h">1h</option><option value="1d">1D</option><option value="1w">1W</option><option value="1M">1M</option></select>
                <button className="remove-condition" onClick={() => onRemoveCondition(condition.id)}><X size={15} /></button>
              </div>
            ))}
          </div>
          <button className="add-condition" onClick={onAddCondition}><Plus size={15} /> Add condition</button>
          <div className="advanced-row"><button className="text-button"><SlidersHorizontal size={14} /> Add nested group</button><span className="muted">Previous-bar offsets and custom formulas are next</span></div>
        </div>
        <div className="panel scan-preview">
          <div className="panel-header"><div><span className="panel-kicker">SIGNAL PREVIEW</span><h3>Scan output</h3></div><span className="result-count">{results.length} matches</span></div>
          <div className="result-toolbar"><div className="search-box"><Search size={15} /><input placeholder="Filter results..." /></div><button className="icon-button"><MoreHorizontal size={17} /></button></div>
          <div className="table-scroll"><table><thead><tr><th>Symbol</th><th>Signal</th><th>LTP</th><th>Change</th><th>Volume</th><th>Score</th></tr></thead><tbody>{results.map((quote) => <tr key={quote.symbol}><td><div className="table-symbol"><span className="symbol-chip">{quote.symbol.slice(0, 2)}</span><div><strong>{quote.symbol}</strong><small>{quote.sector}</small></div></div></td><td><span className={quote.signal === "Momentum" ? "status-badge green-badge" : "status-badge purple-badge"}>{quote.signal}</span></td><td>{formatCurrency(quote.ltp)}</td><td className={quote.changePct >= 0 ? "positive-text" : "negative-text"}>{quote.changePct >= 0 ? "+" : ""}{quote.changePct.toFixed(2)}%</td><td>{formatCompact(quote.volume)}</td><td><div className="score-cell"><span className="score-bar"><i style={{ width: quote.score + "%" }} /></span><strong>{quote.score}</strong></div></td></tr>)}</tbody></table></div>
        </div>
      </div>
    </>
  );
}

function RrgView({ timeframe, onTimeframe }: { timeframe: string; onTimeframe: (value: string) => void }) {
  return (
    <>
      <div className="page-heading compact-heading"><div><div className="eyebrow">RELATIVE STRENGTH · 20-BAR TRAILS</div><h1>RRG radar<span className="accent">.</span></h1><p>See leadership rotation across your selected universe and timeframe.</p></div><div className="heading-actions"><select className="standalone-select" value={timeframe} onChange={(event) => onTimeframe(event.currentTarget.value)}><option value="5m">5 minute</option><option value="15m">15 minute</option><option value="1h">1 hour</option><option value="1d">Daily</option><option value="1w">Weekly</option><option value="1M">Monthly</option><option value="1Y">Yearly</option></select><button className="secondary-button"><Database size={15} /> NIFTY 50</button></div></div>
      <div className="rrg-layout"><div className="panel rrg-panel"><div className="panel-header"><div><span className="panel-kicker">BENCHMARK · NIFTY 50</span><h3>Relative rotation graph</h3></div><div className="rrg-legend"><span><i className="legend-dot green" /> Leading</span><span><i className="legend-dot orange" /> Weakening</span><span><i className="legend-dot blue" /> Improving</span><span><i className="legend-dot red" /> Lagging</span></div></div><RrgChart /></div><div className="panel quadrant-panel"><div className="panel-header"><div><span className="panel-kicker">ROTATION TABLE</span><h3>Current quadrant</h3></div><button className="icon-button"><MoreHorizontal size={17} /></button></div>{demoRrg.map((point) => <div className="rrg-row" key={point.symbol}><div className={"rrg-dot " + point.quadrant} /><div className="rrg-name"><strong>{point.symbol}</strong><small>{point.sector}</small></div><span className="rrg-number">{point.rsRatio.toFixed(1)}</span><span className={"quadrant-text " + point.quadrant}>{point.quadrant}</span></div>)}<div className="rrg-footnote"><ShieldCheck size={14} /> Smooth trails are capped at 20 bars.</div></div></div>
    </>
  );
}

function RrgChart() {
  const colors: Record<string, string> = { leading: "#45d39c", weakening: "#f5a45b", improving: "#4da3ff", lagging: "#ed6a85" };
  return <div className="rrg-chart"><svg viewBox="0 0 760 520" role="img" aria-label="Relative rotation graph demo"><rect x="32" y="20" width="696" height="470" rx="12" fill="#0c1726" stroke="#20324b" /><rect x="380" y="20" width="348" height="235" fill="#17332e" opacity="0.5" /><rect x="32" y="255" width="348" height="235" fill="#331d2a" opacity="0.45" /><line x1="380" x2="380" y1="20" y2="490" stroke="#49617d" strokeDasharray="5 7" /><line x1="32" x2="728" y1="255" y2="255" stroke="#49617d" strokeDasharray="5 7" /><text x="545" y="48" fill="#72e2b7" fontSize="13">LEADING</text><text x="548" y="478" fill="#ef8399" fontSize="13">LAGGING</text><text x="50" y="48" fill="#70b6ff" fontSize="13">IMPROVING</text><text x="50" y="478" fill="#ffc07d" fontSize="13">WEAKENING</text>{demoRrg.map((point, index) => { const x = 380 + (point.rsRatio - 100) * 58; const y = 255 - (point.rsMomentum - 100) * 58; const color = colors[point.quadrant]; const tx = x + (index % 2 ? 10 : -48); const ty = y - 12; return <g key={point.symbol}><line x1={x - 22} y1={y + 20} x2={x} y2={y} stroke={color} strokeWidth="2" opacity="0.38" /><line x1={x - 44} y1={y + 36} x2={x - 22} y2={y + 20} stroke={color} strokeWidth="2" opacity="0.2" /><circle cx={x} cy={y} r="6" fill={color} stroke="#d9efff" strokeWidth="2" /><text x={tx} y={ty} fill="#d9e8f8" fontSize="12" fontWeight="600">{point.symbol}</text></g>; })}<text x="394" y="512" fill="#778ca7" fontSize="11">Relative strength ratio →</text><text x="13" y="265" fill="#778ca7" fontSize="11" transform="rotate(-90 13 265)">Relative momentum →</text></svg></div>;
}

function RrgMini() {
  return <div className="rrg-mini"><div className="mini-axis-x" /><div className="mini-axis-y" />{demoRrg.slice(0, 5).map((point, index) => { const x = 50 + (point.rsRatio - 98) * 18; const y = 52 - (point.rsMomentum - 98) * 18; return <div className={"mini-point " + point.quadrant} style={{ left: x + "%", top: y + "%" }} key={point.symbol}><span>{point.symbol.slice(0, 2)}</span></div>; })}<span className="mini-label mini-leading">Leading</span><span className="mini-label mini-lagging">Lagging</span></div>;
}

function BacktestView() {
  const [running, setRunning] = useState(false);
  const [capital, setCapital] = useState("100000");
  function runBacktest() {
    setRunning(true);
    window.setTimeout(() => setRunning(false), 700);
  }
  return <><div className="page-heading compact-heading"><div><div className="eyebrow">RESEARCH LAB</div><h1>Backtest a strategy<span className="accent">.</span></h1><p>Use the same rule definition for historical validation and paper signals.</p></div><button className="primary-button" onClick={runBacktest}>{running ? <RefreshCw className="spin" size={15} /> : <Play size={15} />}{running ? "Running..." : "Run backtest"}</button></div><div className="backtest-layout"><div className="panel backtest-config"><div className="panel-header"><div><span className="panel-kicker">STRATEGY CONFIGURATION</span><h3>Momentum baseline</h3></div><span className="status-badge orange-badge">Preview</span></div><label>Instrument<input defaultValue="RELIANCE" /></label><label>Timeframe<select defaultValue="1d"><option value="1d">Daily</option><option value="1h">1 hour</option><option value="15m">15 minute</option></select></label><label>Initial capital<input value={capital} onChange={(event) => setCapital(event.currentTarget.value)} /></label><div className="parameter-card"><div><span>Fast EMA</span><strong>21</strong></div><div><span>Slow EMA</span><strong>55</strong></div><div><span>Stop loss</span><strong>2.0%</strong></div></div><div className="warning-card"><ShieldCheck size={16} /><span>No-lookahead checks and realistic charges will be required before trusting results.</span></div><button className="secondary-button full-button" onClick={() => setRunning(true)}><SlidersHorizontal size={15} /> Optimize variables</button></div><div className="panel backtest-results"><div className="panel-header"><div><span className="panel-kicker">RESULTS · DEMO OUTPUT</span><h3>Equity curve</h3></div><div className="result-tabs"><button className="active">Summary</button><button>Trades</button><button>Drawdown</button></div></div><div className="backtest-metrics"><BacktestMetric label="Net return" value="+18.42%" positive /><BacktestMetric label="Max drawdown" value="-8.74%" /><BacktestMetric label="Sharpe ratio" value="1.31" /><BacktestMetric label="Win rate" value="58.3%" positive /></div><div className="equity-chart"><svg viewBox="0 0 720 230"><path d="M0 205 C70 188 88 199 140 160 S210 174 260 132 S330 146 375 102 S440 110 490 88 S570 92 620 48 S675 58 720 24 L720 230 L0 230 Z" fill="#45d39c" opacity="0.12" /><path d="M0 205 C70 188 88 199 140 160 S210 174 260 132 S330 146 375 102 S440 110 490 88 S570 92 620 48 S675 58 720 24" fill="none" stroke="#45d39c" strokeWidth="3" /><line x1="0" x2="720" y1="205" y2="205" stroke="#36506b" strokeDasharray="5 7" /></svg><div className="chart-axis"><span>Jan</span><span>Mar</span><span>May</span><span>Jul</span><span>Aug</span></div></div><div className="backtest-bottom"><span><i className="legend-dot green" /> Strategy equity</span><span>42 trades</span><span>Capital: {formatCurrency(Number(capital) || 0)}</span></div></div></div></>;
}

function BacktestMetric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return <div className="backtest-metric"><span>{label}</span><strong className={positive ? "positive-text" : ""}>{value}</strong></div>;
}

function OptionsView() {
  return <><div className="page-heading compact-heading"><div><div className="eyebrow">DERIVATIVES DESK</div><h1>Option chain<span className="accent">.</span></h1><p>Inspect open interest, IV and payoff context before building a paper position.</p></div><div className="heading-actions"><button className="secondary-button"><RefreshCw size={15} /> Refresh</button><button className="primary-button"><Plus size={15} /> Build strategy</button></div></div><div className="option-summary"><div className="option-underlying"><span>NIFTY 50</span><strong>24,500</strong><small className="positive-text">+0.84% today</small></div><div><span>Expiry</span><strong>Nearest weekly</strong></div><div><span>ATM IV</span><strong>12.8%</strong></div><div><span>PCR</span><strong>0.92</strong></div><div><span>Max pain</span><strong>24,400</strong></div></div><div className="panel option-panel"><div className="panel-header"><div><span className="panel-kicker">CALLS · PUTS · OPEN INTEREST</span><h3>NIFTY option chain</h3></div><div className="chain-actions"><button className="chain-toggle active">OI</button><button className="chain-toggle">Change OI</button><button className="icon-button"><MoreHorizontal size={17} /></button></div></div><div className="table-scroll"><table className="option-table"><thead><tr><th colSpan={3}>CALLS</th><th>STRIKE</th><th colSpan={3}>PUTS</th><th>IV</th></tr><tr><th>LTP</th><th>OI</th><th>Change OI</th><th></th><th>LTP</th><th>OI</th><th>Change OI</th><th></th></tr></thead><tbody>{optionRows.map((row) => <tr className={row.strike === 24500 ? "atm-row" : ""} key={row.strike}><td className="call-cell">{row.callLtp}</td><td>{formatCompact(row.callOi)}</td><td className={row.callChangeOi >= 0 ? "positive-text" : "negative-text"}>{row.callChangeOi >= 0 ? "+" : ""}{formatCompact(row.callChangeOi)}</td><td className="strike-cell">{row.strike}</td><td className="put-cell">{row.putLtp}</td><td>{formatCompact(row.putOi)}</td><td className={row.putChangeOi >= 0 ? "positive-text" : "negative-text"}>{row.putChangeOi >= 0 ? "+" : ""}{formatCompact(row.putChangeOi)}</td><td>{row.iv}%</td></tr>)}</tbody></table></div></div></>;
}

function ArbitrageView() {
  return <><div className="page-heading compact-heading"><div><div className="eyebrow">CROSS-VENUE RESEARCH</div><h1>Arbitrage scanner<span className="accent">.</span></h1><p>Compare executable spreads after fees, slippage, latency and transfer costs.</p></div><button className="primary-button"><RefreshCw size={15} /> Scan venues</button></div><div className="arbitrage-grid"><div className="panel arb-status"><div className="arb-icon"><Zap size={22} /></div><span className="panel-kicker">PAPER MODE</span><h3>No live opportunities</h3><p>Crypto exchange connectors are not enabled yet. The scanner will reject false spreads after fee and latency checks.</p><div className="check-list"><CheckLine label="Trading fees" /><CheckLine label="Slippage estimate" /><CheckLine label="Transfer and withdrawal cost" /><CheckLine label="Funding rate" /><CheckLine label="Execution latency" /></div></div><div className="panel"><div className="panel-header"><div><span className="panel-kicker">MONITORING PLAN</span><h3>Arbitrage types</h3></div><span className="status-badge purple-badge">Research</span></div><div className="arb-type"><div className="type-icon blue"><ArrowUpRight size={17} /></div><div><strong>Cross-exchange spot</strong><span>Buy on one venue, sell on another</span></div><span className="muted">Later</span></div><div className="arb-type"><div className="type-icon green"><Activity size={17} /></div><div><strong>Spot-futures basis</strong><span>Capture funding and basis spread</span></div><span className="muted">Later</span></div><div className="arb-type"><div className="type-icon orange"><RefreshCw size={17} /></div><div><strong>Triangular routes</strong><span>Three-leg price inconsistency</span></div><span className="muted">Later</span></div></div></div></>;
}

function CheckLine({ label }: { label: string }) {
  return <div className="check-line"><ShieldCheck size={14} /><span>{label}</span><span className="muted">Ready</span></div>;
}

function SettingsView() {
  const [connecting, setConnecting] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState("");

  async function testConnection() {
    setConnecting(true);
    setConnectionMessage("");
    try {
      const response = await fetch(API_URL + "/api/v1/broker/read-only-connect", { method: "POST" });
      const data = await response.json();
      if (data.status) {
        setConnectionMessage("Read-only SmartAPI session established. No order permissions were used.");
      } else {
        setConnectionMessage(data.message || "SmartAPI connection was not established.");
      }
    } catch {
      setConnectionMessage("Backend unavailable. Start the FastAPI service and try again.");
    } finally {
      setConnecting(false);
    }
  }

  return <><div className="page-heading compact-heading"><div><div className="eyebrow">PRIVATE WORKSPACE</div><h1>Settings<span className="accent">.</span></h1><p>Manage local data sources, safety switches and future platform connections.</p></div></div><div className="settings-grid"><div className="panel"><div className="panel-header"><div><span className="panel-kicker">EXECUTION SAFETY</span><h3>Trading controls</h3></div><ShieldCheck className="green-icon" size={20} /></div><SettingToggle title="Paper trading" detail="All orders are simulated locally" enabled /><SettingToggle title="Live trading" detail="Disabled until explicit review" enabled={false} locked /><SettingToggle title="AI order authority" detail="Research assistant cannot place orders" enabled={false} locked /></div><div className="panel"><div className="panel-header"><div><span className="panel-kicker">DATA CONNECTION</span><h3>Angel One SmartAPI</h3></div><span className="status-badge orange-badge">Not connected</span></div><div className="secure-field"><Database size={16} /><div><strong>Backend-only secret storage</strong><span>Credentials load from local .env and never enter web or mobile bundles.</span></div></div><button className="secondary-button full-button" onClick={testConnection}>{connecting ? <RefreshCw className="spin" size={15} /> : <Settings size={15} />}{connecting ? "Testing..." : "Test read-only connection"}</button><div className="settings-note"><ShieldCheck size={14} />{connectionMessage || "This test creates only a read-only data session and does not place an order."}</div><div className="settings-note"><ShieldCheck size={14} /> Use rotated credentials only. Live order placement is intentionally unavailable in this build.</div></div><div className="panel"><div className="panel-header"><div><span className="panel-kicker">PLATFORM CLIENTS</span><h3>Web · Android · iOS</h3></div><Sparkles className="violet-icon" size={20} /></div><div className="client-row"><div className="client-status ready">WEB</div><span>Responsive research terminal</span><span className="status-badge green-badge">Ready</span></div><div className="client-row"><div className="client-status">AND</div><span>Expo mobile client</span><span className="status-badge purple-badge">Foundation</span></div><div className="client-row"><div className="client-status">iOS</div><span>Expo mobile client</span><span className="status-badge purple-badge">Foundation</span></div></div></div></>;
}

function SettingToggle({ title, detail, enabled, locked }: { title: string; detail: string; enabled: boolean; locked?: boolean }) {
  return <div className="setting-toggle"><div><strong>{title}</strong><span>{detail}</span></div><button className={enabled ? "toggle toggle-on" : "toggle"} disabled={locked}><i /></button></div>;
}

function ActionItem({ icon: Icon, title, detail, onClick }: { icon: LucideIcon; title: string; detail: string; onClick: () => void }) {
  return <button className="action-item" onClick={onClick}><div className="action-icon"><Icon size={16} /></div><div><strong>{title}</strong><span>{detail}</span></div><ChevronRight size={16} /></button>;
}

export default App;
