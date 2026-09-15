import { useMemo, useState } from "react";
import { Database, FlaskConical, Play, RefreshCw, ShieldCheck, SlidersHorizontal } from "lucide-react";
import "./BacktestLab.css";

type MetricMap = Record<string, number | null>;
type CurvePoint = { time: string; equity: number; buyHold: number; drawdownPct: number };
type TradeRow = {
  EntryTime: string; ExitTime: string; EntryFill: number; ExitFill: number; BarsHeld: number;
  NetReturnPct: number; PnL: number; Fees: number; MFE_Pct: number; MAE_Pct: number; ForcedExit: boolean;
};
type RobustnessRow = Record<string, string | number | null>;
type BacktestResult = {
  mode: "single" | "nifty50_batch";
  strategy: string;
  symbol?: string;
  timeframe: string;
  dataSource: string;
  coverage: Record<string, string | number>;
  verdict: string;
  verdictReasons: string[];
  metrics: MetricMap;
  equityCurve: CurvePoint[];
  trades?: TradeRow[];
  robustness?: {
    outOfSample: RobustnessRow[];
    nearbyParameters: RobustnessRow[];
    execution: RobustnessRow[];
    costStress: RobustnessRow[];
  };
  diagnostics?: Record<string, number | null>;
  stocks?: Array<Record<string, string | number | null>>;
  errors?: string[];
  warnings: string[];
};

type Tab = "summary" | "trades" | "robustness" | "universe";
type Mode = "single" | "nifty50_batch";
type Props = { apiUrl: string };

const timeframes = [
  ["15m", "15 minute"], ["30m", "30 minute"], ["1h", "1 hour"], ["4h", "4 hour"], ["1d", "Daily"], ["1wk", "Weekly"],
] as const;

function number(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : value.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function money(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "—" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

function percent(value: number | null | undefined, digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : ""}${number(value, digits)}%`;
}

function metric(result: BacktestResult | null, key: string): number | null {
  return result?.metrics?.[key] ?? null;
}

function linePath(points: CurvePoint[], key: "equity" | "buyHold", width = 720, height = 220): string {
  if (points.length < 2) return "";
  const values = points.flatMap((point) => [point.equity, point.buyHold]).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  return points.map((point, index) => {
    const x = (index / Math.max(points.length - 1, 1)) * width;
    const y = height - ((point[key] - min) / span) * (height - 24) - 12;
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
}

function EquityChart({ points }: { points: CurvePoint[] }) {
  const strategy = useMemo(() => linePath(points, "equity"), [points]);
  const benchmark = useMemo(() => linePath(points, "buyHold"), [points]);
  if (points.length < 2) return <div className="quant-empty">Run a backtest to draw the equity curve.</div>;
  const first = new Date(points[0].time).toLocaleDateString("en-IN", { year: "numeric", month: "short" });
  const last = new Date(points[points.length - 1].time).toLocaleDateString("en-IN", { year: "numeric", month: "short" });
  return <div className="quant-chart">
    <svg viewBox="0 0 720 230" role="img" aria-label="Strategy and buy and hold equity curves">
      {[45, 95, 145, 195].map((y) => <line key={y} x1="0" x2="720" y1={y} y2={y} className="quant-grid-line" />)}
      <path d={benchmark} className="quant-benchmark-path" />
      <path d={strategy} className="quant-equity-path" />
    </svg>
    <div className="quant-chart-axis"><span>{first}</span><span>{last}</span></div>
    <div className="quant-chart-legend"><span><i className="quant-dot strategy" /> Strategy</span><span><i className="quant-dot benchmark" /> Buy & hold</span></div>
  </div>;
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) {
  return <div className="backtest-metric quant-metric"><span>{label}</span><strong className={tone === "positive" ? "positive-text" : tone === "negative" ? "negative-text" : ""}>{value}</strong></div>;
}

function GenericTable({ rows }: { rows: RobustnessRow[] }) {
  if (!rows.length) return <div className="quant-empty">No rows for this test.</div>;
  const keys = Object.keys(rows[0]);
  return <div className="table-scroll quant-table"><table><thead><tr>{keys.map((key) => <th key={key}>{key.replaceAll(/([A-Z])/g, " $1")}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{keys.map((key) => <td key={key}>{typeof row[key] === "number" ? number(row[key] as number, 3) : String(row[key] ?? "—")}</td>)}</tr>)}</tbody></table></div>;
}

export default function BacktestLab({ apiUrl }: Props) {
  const [mode, setMode] = useState<Mode>("single");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [timeframe, setTimeframe] = useState("1d");
  const [startDate, setStartDate] = useState("2016-09-15");
  const [endDate, setEndDate] = useState("2026-09-15");
  const [source, setSource] = useState("auto");
  const [capital, setCapital] = useState("100000");
  const [rsiThreshold, setRsiThreshold] = useState("10");
  const [vertexEntry, setVertexEntry] = useState("-10");
  const [vertexExit, setVertexExit] = useState("-10");
  const [feeBps, setFeeBps] = useState("12");
  const [slippageBps, setSlippageBps] = useState("3");
  const [fillMode, setFillMode] = useState("next_open");
  const [matchExport, setMatchExport] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [tab, setTab] = useState<Tab>("summary");

  const batchIntradayNeedsAngel = mode === "nifty50_batch" && ["15m", "30m", "1h", "4h"].includes(timeframe) && source !== "angel_one";

  async function runBacktest() {
    setRunning(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/backtest/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          symbol: symbol.trim().toUpperCase(),
          timeframe,
          start_date: startDate,
          end_date: endDate,
          initial_capital: Number(capital),
          rsi_length: 3,
          rsi_entry_threshold: Number(rsiThreshold),
          vertex_length: 14,
          vertex_entry_threshold: Number(vertexEntry),
          vertex_exit_threshold: Number(vertexExit),
          match_export: matchExport,
          fill_mode: fillMode,
          fee_bps_per_side: Number(feeBps),
          slippage_bps_per_side: Number(slippageBps),
          source,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Backtest request failed.");
      setResult(data as BacktestResult);
      setTab("summary");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Backtest failed.");
    } finally {
      setRunning(false);
    }
  }

  const promising = result?.verdict?.startsWith("PROMISING") ?? false;
  const trades = result?.trades ?? [];
  const stocks = result?.stocks ?? [];
  const warnings = result?.warnings ?? [];

  return <>
    <div className="page-heading compact-heading">
      <div><div className="eyebrow">VERTEX + RSI QUANT RESEARCH</div><h1>Backtest Lab<span className="accent">.</span></h1><p>Test completed-bar signals with realistic execution, costs, drawdowns, expectancy and robustness checks.</p></div>
      <button className="primary-button" onClick={runBacktest} disabled={running || batchIntradayNeedsAngel}>{running ? <RefreshCw className="spin" size={15} /> : <Play size={15} />}{running ? "Running research…" : "Run backtest"}</button>
    </div>

    <div className="quant-mode-switch">
      <button className={mode === "single" ? "active" : ""} onClick={() => setMode("single")}>Single symbol</button>
      <button className={mode === "nifty50_batch" ? "active" : ""} onClick={() => setMode("nifty50_batch")}>NIFTY 50 · 10 year batch</button>
    </div>

    <div className="backtest-layout quant-layout">
      <div className="panel backtest-config quant-config">
        <div className="panel-header"><div><span className="panel-kicker">STRATEGY CONFIGURATION</span><h3>Vertex + RSI(3)</h3></div><span className="status-badge green-badge">Real engine</span></div>
        {mode === "single" && <label>Instrument<input value={symbol} onChange={(event) => setSymbol(event.currentTarget.value.toUpperCase())} placeholder="RELIANCE" /></label>}
        <label>Timeframe<select value={timeframe} onChange={(event) => setTimeframe(event.currentTarget.value)}>{timeframes.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <div className="quant-two"><label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.currentTarget.value)} /></label><label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.currentTarget.value)} /></label></div>
        <label>Market data<select value={source} onChange={(event) => setSource(event.currentTarget.value)}><option value="auto">Auto · Angel intraday / Yahoo long-term</option><option value="yahoo">Yahoo Finance</option><option value="angel_one">Angel One SmartAPI</option></select></label>
        <label>{mode === "single" ? "Initial capital" : "Total portfolio capital"}<input type="number" min="1000" value={capital} onChange={(event) => setCapital(event.currentTarget.value)} /></label>

        <div className="quant-rule-card"><strong>Entry</strong><span>RSI(3) &lt; {rsiThreshold || "10"} AND Vertex &lt; {vertexEntry || "-10"}</span><strong>Exit</strong><span>Vertex &gt; {vertexExit || "-10"}</span></div>
        <div className="quant-two"><label>RSI entry &lt;<input type="number" step="0.5" value={rsiThreshold} onChange={(event) => setRsiThreshold(event.currentTarget.value)} /></label><label>Vertex entry &lt;<input type="number" step="0.5" value={vertexEntry} onChange={(event) => setVertexEntry(event.currentTarget.value)} /></label></div>
        <label>Vertex exit &gt;<input type="number" step="0.5" value={vertexExit} onChange={(event) => setVertexExit(event.currentTarget.value)} /></label>
        <label>Execution<select value={fillMode} onChange={(event) => setFillMode(event.currentTarget.value)}><option value="next_open">Next bar open · recommended</option><option value="signal_close">Signal close · optimistic comparator</option></select></label>
        <div className="quant-check"><input id="match-export" type="checkbox" checked={matchExport} onChange={(event) => setMatchExport(event.currentTarget.checked)} /><label htmlFor="match-export"><strong>Match exported Vertex</strong><span>Use the Pine-compatible one-bar delay.</span></label></div>
        <div className="quant-two"><label>Fees / side (bps)<input type="number" min="0" step="1" value={feeBps} onChange={(event) => setFeeBps(event.currentTarget.value)} /></label><label>Slippage / side (bps)<input type="number" min="0" step="1" value={slippageBps} onChange={(event) => setSlippageBps(event.currentTarget.value)} /></label></div>

        {batchIntradayNeedsAngel && <div className="warning-card"><ShieldCheck size={16} /><span>Ten-year NIFTY 50 intraday research requires Angel One. Select Angel One SmartAPI as the data source.</span></div>}
        <div className="settings-note"><ShieldCheck size={14} /> Signals are evaluated only on completed candles. Default fills occur at the next bar open to avoid close-price look-ahead assumptions.</div>
      </div>

      <div className="panel backtest-results quant-results">
        <div className="panel-header"><div><span className="panel-kicker">{result ? `${result.mode === "single" ? result.symbol : "NIFTY 50"} · ${result.timeframe} · ${result.dataSource}` : "AWAITING TEST"}</span><h3>{result ? result.verdict : "Research scorecard"}</h3></div>{result && <span className={`status-badge ${promising ? "green-badge" : "orange-badge"}`}>{promising ? "Promising" : "Research only"}</span>}</div>

        {error && <div className="quant-error"><ShieldCheck size={15} />{error}</div>}
        {!result && !error && <div className="quant-empty quant-empty-large"><FlaskConical size={28} /><strong>Run the exact Vertex + RSI strategy</strong><span>Results will include EV, drawdown, loss streaks, risk-adjusted returns, full trades and robustness checks.</span></div>}

        {result && <>
          <div className="backtest-metrics quant-primary-metrics">
            <MetricCard label="Net return" value={percent(metric(result, "Total Return %"))} tone={(metric(result, "Total Return %") ?? 0) > 0 ? "positive" : "negative"} />
            <MetricCard label="EV / trade" value={percent(metric(result, "EV / Trade %"), 3)} tone={(metric(result, "EV / Trade %") ?? 0) > 0 ? "positive" : "negative"} />
            <MetricCard label="Profit factor" value={number(metric(result, "Profit Factor"))} />
            <MetricCard label="Max drawdown" value={percent(metric(result, "Max Drawdown %"))} tone="negative" />
            <MetricCard label="Sharpe" value={number(metric(result, "Sharpe (daily)"))} />
            <MetricCard label="Win rate" value={percent(metric(result, "Win Rate %"))} />
            <MetricCard label="Trades" value={number(metric(result, "Trades"), 0)} />
            <MetricCard label="Max losing streak" value={number(metric(result, "Max Losing Streak"), 0)} />
          </div>
          <EquityChart points={result.equityCurve} />
          <div className="quant-verdict-reasons">{result.verdictReasons.map((reason) => <div key={reason}><ShieldCheck size={14} /><span>{reason}</span></div>)}</div>
          <div className="backtest-bottom quant-bottom"><span><i className="legend-dot green" /> Strategy equity</span><span>{String(result.coverage.bars ?? result.coverage.testedStocks ?? "—")} {result.mode === "single" ? "bars" : "stocks"}</span><span>{String(result.coverage.from ?? "").slice(0, 10)} → {String(result.coverage.to ?? "").slice(0, 10)}</span><span>Ending: {money(metric(result, "Ending Equity"))}</span></div>
        </>}
      </div>
    </div>

    {result && <div className="panel quant-detail-panel">
      <div className="result-tabs quant-tabs">
        <button className={tab === "summary" ? "active" : ""} onClick={() => setTab("summary")}>All metrics</button>
        {result.mode === "single" && <button className={tab === "trades" ? "active" : ""} onClick={() => setTab("trades")}>Trades · {trades.length}</button>}
        {result.mode === "single" && <button className={tab === "robustness" ? "active" : ""} onClick={() => setTab("robustness")}>Robustness</button>}
        {result.mode === "nifty50_batch" && <button className={tab === "universe" ? "active" : ""} onClick={() => setTab("universe")}>NIFTY 50 stocks · {stocks.length}</button>}
      </div>

      {tab === "summary" && <div className="quant-summary-grid">
        {Object.entries(result.metrics).map(([key, value]) => <div className="quant-summary-row" key={key}><span>{key}</span><strong>{key.includes("Equity") || key.includes("Profit") && !key.includes("Factor") || key.includes("Amount") || key === "Total Fees" ? money(value) : key.includes("%") || key.includes("VaR") || key.includes("CVaR") ? percent(value) : number(value)}</strong></div>)}
        {result.diagnostics && Object.entries(result.diagnostics).map(([key, value]) => <div className="quant-summary-row" key={`diag-${key}`}><span>{key.replaceAll(/([A-Z])/g, " $1")}</span><strong>{number(value)}</strong></div>)}
      </div>}

      {tab === "trades" && <div className="table-scroll quant-table"><table><thead><tr><th>Entry</th><th>Exit</th><th>Entry fill</th><th>Exit fill</th><th>Bars</th><th>Net return</th><th>P&L</th><th>Fees</th><th>MFE</th><th>MAE</th></tr></thead><tbody>{trades.map((trade, index) => <tr key={`${trade.EntryTime}-${index}`}><td>{trade.EntryTime.slice(0, 16).replace("T", " ")}</td><td>{trade.ExitTime.slice(0, 16).replace("T", " ")}</td><td>{number(trade.EntryFill)}</td><td>{number(trade.ExitFill)}</td><td>{trade.BarsHeld}</td><td className={trade.NetReturnPct > 0 ? "positive-text" : "negative-text"}>{percent(trade.NetReturnPct)}</td><td>{money(trade.PnL)}</td><td>{money(trade.Fees)}</td><td>{percent(trade.MFE_Pct)}</td><td>{percent(trade.MAE_Pct)}</td></tr>)}</tbody></table>{!trades.length && <div className="quant-empty">No completed trades in this sample.</div>}</div>}

      {tab === "robustness" && result.robustness && <div className="quant-robust-grid">
        <section><div className="quant-section-heading"><div><span className="panel-kicker">OUT OF SAMPLE</span><h3>First 70% vs last 30%</h3></div><ShieldCheck size={18} /></div><GenericTable rows={result.robustness.outOfSample} /></section>
        <section><div className="quant-section-heading"><div><span className="panel-kicker">PARAMETER STABILITY</span><h3>Nearby RSI / Vertex settings</h3></div><SlidersHorizontal size={18} /></div><GenericTable rows={result.robustness.nearbyParameters} /></section>
        <section><div className="quant-section-heading"><div><span className="panel-kicker">EXECUTION REALISM</span><h3>Next-open vs signal-close</h3></div><Database size={18} /></div><GenericTable rows={result.robustness.execution} /></section>
        <section><div className="quant-section-heading"><div><span className="panel-kicker">COST STRESS</span><h3>Fees + slippage sensitivity</h3></div><Database size={18} /></div><GenericTable rows={result.robustness.costStress} /></section>
      </div>}

      {tab === "universe" && <div className="table-scroll quant-table"><table><thead><tr><th>Symbol</th><th>Company</th><th>Trades</th><th>Return</th><th>EV / trade</th><th>PF</th><th>Max DD</th><th>Sharpe</th><th>Win rate</th></tr></thead><tbody>{stocks.map((stock) => <tr key={String(stock.symbol)}><td><strong>{String(stock.symbol)}</strong></td><td>{String(stock.company)}</td><td>{number(stock.Trades as number | null, 0)}</td><td>{percent(stock["Total Return %"] as number | null)}</td><td>{percent(stock["EV / Trade %"] as number | null, 3)}</td><td>{number(stock["Profit Factor"] as number | null)}</td><td>{percent(stock["Max Drawdown %"] as number | null)}</td><td>{number(stock["Sharpe (daily)"] as number | null)}</td><td>{percent(stock["Win Rate %"] as number | null)}</td></tr>)}</tbody></table></div>}

      {warnings.length > 0 && <div className="quant-warning-list">{warnings.map((warning) => <div key={warning}><ShieldCheck size={14} /><span>{warning}</span></div>)}</div>}
      {!!result.errors?.length && <div className="quant-warning-list">{result.errors.slice(0, 12).map((item) => <div key={item}><ShieldCheck size={14} /><span>{item}</span></div>)}</div>}
    </div>}
  </>;
}
