import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  Modal,
  Pressable,
  SafeAreaView,
  SectionList,
  TextInput,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

declare const process: { env: Record<string, string | undefined> };

type Tab = "home" | "scan" | "rrg" | "research" | "orders";
type Logic = "all" | "any";
type Operator = ">" | "<" | ">=" | "<=" | "=" | "!=" | "contains" | "not_contains" | "starts_with" | "ends_with" | "crosses_above" | "crosses_below";
type Availability = "ready" | "metadata_required" | "tick_feed_required" | "depth_feed_required" | "depth_history_required" | "fundamentals_required" | "shareholding_required" | "cashflow_required";

type FieldParameter = {
  name: string;
  label: string;
  type: "number" | "text" | "select" | "field";
  default: number | string;
  min?: number;
  max?: number;
  options?: string[];
};

type ScreenerField = {
  id: string;
  label: string;
  category: string;
  kind: "field" | "function" | "indicator" | "measure" | "group";
  valueType: "number" | "string" | "group";
  description: string;
  availability: Availability;
  parameters: FieldParameter[];
};

type ScreenerCategory = { id: string; label: string; items: ScreenerField[] };
type ConditionState = {
  id: string;
  field: string;
  operator: Operator;
  value: number | string;
  timeframe: string;
  lookback: number;
  parameters: Record<string, number | string | boolean>;
  compare_field?: string;
  compare_parameters?: Record<string, number | string | boolean>;
};
type FilterGroup = { id: string; logic: Logic; conditions: ConditionState[] };
type PickerTarget = { conditionId: string; groupId?: string; mode: "primary" | "compare" | "parameter" | "compare_parameter"; parameterName?: string };
type DisplayQuote = { symbol: string; price: string; change: string; signal: string; color: string };
type EodhdStatus = { configured: boolean; defaultExchange: string; message: string };

const colors = {
  bg: "#08111f",
  panel: "#0e1b2c",
  panelLight: "#13263c",
  line: "#203650",
  text: "#e4eef9",
  muted: "#7b92ad",
  blue: "#58adff",
  green: "#45d39c",
  purple: "#a08eff",
  orange: "#f5a45b",
  red: "#ed6a85",
};

const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://127.0.0.1:8000";
const fundamentalSyncSymbols = ["RELIANCE", "ICICIBANK", "BHARTIARTL", "TCS", "HDFCBANK", "SUNPHARMA", "INFY", "AXISBANK"];

const operatorLabels: Record<Operator, string> = {
  "=": "Equals",
  "!=": "Not equals",
  ">": "Greater than",
  ">=": "Greater than or equal to",
  "<": "Less than",
  "<=": "Less than or equal to",
  contains: "Contains",
  not_contains: "Does not contain",
  starts_with: "Starts with",
  ends_with: "Ends with",
  crosses_above: "Crossed above",
  crosses_below: "Crossed below",
};

function availabilityLabel(availability: Availability): string {
  if (availability === "fundamentals_required") return "FINANCIAL DATA";
  if (availability === "shareholding_required") return "SHAREHOLDING";
  if (availability === "cashflow_required") return "CASH FLOW";
  if (availability === "depth_history_required") return "DEPTH HISTORY";
  if (availability === "depth_feed_required") return "MARKET DEPTH";
  if (availability === "tick_feed_required") return "TICK DATA";
  if (availability === "metadata_required") return "METADATA";
  return "READY";
}

const quotes: DisplayQuote[] = [
  { symbol: "RELIANCE", price: "₹2,942.40", change: "+1.84%", signal: "Momentum", color: colors.green },
  { symbol: "SUNPHARMA", price: "₹1,742.30", change: "+2.32%", signal: "Momentum", color: colors.green },
  { symbol: "ICICIBANK", price: "₹1,328.65", change: "+1.25%", signal: "Momentum", color: colors.green },
  { symbol: "TCS", price: "₹4,120.75", change: "-0.22%", signal: "Watch", color: colors.orange },
];

const sourceParameter: FieldParameter = { name: "source", label: "Input field", type: "field", default: "close" };
const periodParameter: FieldParameter = { name: "period", label: "Period", type: "number", default: 20, min: 1, max: 500 };
const groupParameter: FieldParameter = { name: "groupBy", label: "Group by", type: "select", default: "sector", options: ["sector", "industry", "marketcapname"] };

function fieldDefinition(
  id: string,
  label: string,
  category: string,
  options: Partial<Omit<ScreenerField, "id" | "label" | "category">> = {},
): ScreenerField {
  return {
    id,
    label,
    category,
    kind: "field",
    valueType: ["symbol", "industry", "sector", "marketcapname"].includes(id) ? "string" : "number",
    description: "",
    availability: "ready",
    parameters: [],
    ...options,
  };
}

function basicFields(category: string, entries: Array<[string, string]>, availability: Availability = "ready", kind: ScreenerField["kind"] = "field"): ScreenerField[] {
  return entries.map(([id, label]) => fieldDefinition(id, label, category, { availability, kind }));
}

const fallbackCatalog: ScreenerCategory[] = [
  { id: "measures", label: "Measures", items: [
    fieldDefinition("sub_filter", "Sub-Filter / Group", "measures", { kind: "group", valueType: "group" }),
    fieldDefinition("number", "Number", "measures", { kind: "measure" }),
  ] },
  { id: "stock_attributes", label: "Stock attributes", items: basicFields("stock_attributes", [
    ["symbol", "Symbol"], ["industry", "Industry"], ["sector", "Sector"], ["marketcapname", "Marketcap name"], ["open", "Open"], ["high", "High"], ["low", "Low"], ["close", "Close"], ["volume", "Volume"], ["change_pct", "% Change"], ["vwap", "VWAP"], ["ha_open", "HA-Open (Heikin-Ashi)"], ["ha_high", "HA-High (Heikin-Ashi)"], ["ha_low", "HA-Low (Heikin-Ashi)"], ["ha_close", "HA-Close (Heikin-Ashi)"], ["fno_lot_size", "FnO lot size"], ["hl2", "HL2"], ["hlc3", "HLC3"], ["ohlc4", "OHLC4"],
  ]).map((item) => ["industry", "sector", "marketcapname", "fno_lot_size"].includes(item.id) ? { ...item, availability: "metadata_required" as const } : item) },
  { id: "trade_book", label: "Trade Book fields", items: basicFields("trade_book", [
    ["buyer_initiated_trades", "Buyer initiated trades"], ["buyer_initiated_trades_quantity", "Buyer initiated trades quantity"], ["buyer_initiated_trades_avg_quantity", "Buyer initiated trades average quantity"], ["seller_initiated_trades", "Seller initiated trades"], ["seller_initiated_trades_quantity", "Seller initiated trades quantity"], ["seller_initiated_trades_avg_quantity", "Seller initiated trades average quantity"], ["buyer_seller_trades_ratio", "Buyer vs Seller initiated trades ratio"], ["buyer_seller_trade_quantity_ratio", "Buyer vs Seller initiated trades quantity ratio"], ["buyer_initiated_vwap", "Buyer initiated trades VWAP"], ["seller_initiated_vwap", "Seller initiated trades VWAP"],
  ], "tick_feed_required") },
  { id: "order_book", label: "Order Book fields", items: basicFields("order_book", [
    ["orders", "Orders"], ["orders_quantity", "Orders Quantity"], ["buy_orders", "Buy Orders"], ["buy_orders_quantity", "Buy Orders Quantity"], ["sell_orders", "Sell Orders"], ["sell_orders_quantity", "Sell Orders Quantity"], ["buy_sell_orders_ratio", "Buy vs Sell orders ratio"], ["buy_sell_order_quantity_ratio", "Buy vs Sell orders quantity ratio"], ["cancelled_buy_orders", "Cancelled Buy Orders"], ["cancelled_buy_orders_quantity", "Cancelled Buy Orders Quantity"], ["cancelled_sell_orders", "Cancelled Sell Orders"], ["cancelled_sell_orders_quantity", "Cancelled Sell Orders Quantity"], ["total_cancelled_orders", "Total Cancelled orders"], ["total_cancelled_orders_quantity", "Total Cancelled orders quantity"], ["cancelled_orders_ratio", "Cancelled orders ratio"], ["cancelled_order_quantity_ratio", "Cancelled orders quantity ratio"], ["buy_orders_vwap", "Buy Orders VWAP"], ["sell_orders_vwap", "Sell Orders VWAP"], ["orders_vwap", "Orders VWAP"],
  ], "depth_feed_required").map((item) => item.id.includes("cancelled") ? { ...item, availability: "depth_history_required" as const } : item) },
  { id: "group_functions", label: "Group Functions", items: [
    fieldDefinition("group_count", "GroupCount (total rows in a group)", "group_functions", { kind: "function", parameters: [groupParameter] }),
    ...["low", "high", "avg", "sum"].map((name) => fieldDefinition(`group_${name}`, `Group${name[0].toUpperCase() + name.slice(1)} (${name} of the group)`, "group_functions", { kind: "function", parameters: [sourceParameter, groupParameter] })),
  ] },
  { id: "math_functions", label: "Math Functions", items: [
    fieldDefinition("bracket", "Bracket (value)", "math_functions", { kind: "function", parameters: [sourceParameter] }),
    fieldDefinition("min", "Min (duration, value)", "math_functions", { kind: "function", parameters: [periodParameter, sourceParameter] }),
    fieldDefinition("max", "Max (duration, value)", "math_functions", { kind: "function", parameters: [periodParameter, sourceParameter] }),
    ...basicFields("math_functions", [["greatest", "Greatest (fields..)"], ["least", "Least (fields..)"], ["count", "Count (duration, filter)"], ["countstreak", "Countstreak (duration, filter)"], ["abs", "Abs (value)"], ["ceil", "Ceil (value)"], ["floor", "Floor (value)"], ["round", "Round (value)"], ["square", "Square (value)"], ["sqrt", "Square root (value)"], ["log", "Log (value)"], ["log10", "Log10 (value)"]], "ready", "function").map((item) => ({ ...item, parameters: [sourceParameter] })),
  ] },
  { id: "pivots", label: "Pivots", items: basicFields("pivots", [["pivot_point", "Pivot point"], ["pivot_r1", "Pivot point R1"], ["pivot_r2", "Pivot point R2"], ["pivot_r3", "Pivot point R3"], ["pivot_s1", "Pivot point S1"], ["pivot_s2", "Pivot point S2"], ["pivot_s3", "Pivot point S3"]]) },
  { id: "indicators", label: "Indicators", items: [
    fieldDefinition("rsi", "RSI", "indicators", { kind: "indicator", parameters: [{ ...periodParameter, default: 14, min: 2, max: 200 }] }),
    ...basicFields("indicators", [["sma", "SMA (Simple)"], ["ema", "EMA (Exponential)"], ["wma", "WMA (Weighted)"], ["tma", "TMA (Triangular)"], ["rma", "RMA (Rolling Moving Average)"], ["tema", "TEMA (Triple EMA)"], ["hma", "HMA (Hull moving average)"], ["vwma", "VWMA (Volume-weighted avg)"], ["std", "Std (Standard Deviation)"], ["sum", "Sum (total for the given period)"], ["bollinger_upper", "Upper Bollinger band"], ["bollinger_middle", "Middle Bollinger band"], ["bollinger_lower", "Lower Bollinger band"]], "ready", "indicator").map((item) => ({ ...item, parameters: [periodParameter, sourceParameter] })),
    fieldDefinition("parabolic_sar", "Parabolic SAR", "indicators", { kind: "indicator", parameters: [{ name: "step", label: "Step", type: "number", default: 0.02 }, { name: "maximum", label: "Maximum", type: "number", default: 0.2 }] }),
    fieldDefinition("score", "Momentum score", "indicators", { kind: "indicator" }),
  ] },
];

const defaultMobileConditions: ConditionState[] = [
  { id: "rsi", field: "rsi", operator: ">", value: 50, timeframe: "1d", lookback: 0, parameters: { period: 14 } },
  { id: "change", field: "change_pct", operator: ">", value: 0, timeframe: "1d", lookback: 0, parameters: {} },
  { id: "volume", field: "volume", operator: ">", value: 1000000, timeframe: "1d", lookback: 0, parameters: {} },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("home");

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <View style={styles.logo}><Text style={styles.logoText}>A</Text></View>
        <View style={styles.headerTitle}>
          <Text style={styles.title}>ALL IN ONE</Text>
          <Text style={styles.subtitle}>TRADING LAB</Text>
        </View>
        <View style={styles.mode}><View style={styles.dot} /><Text style={styles.modeText}>PAPER</Text></View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === "home" && <HomeScreen onTab={setTab} />}
        {tab === "scan" && <ScanScreen />}
        {tab === "rrg" && <RrgScreen />}
        {tab === "research" && <ResearchScreen />}
        {tab === "orders" && <OrdersScreen />}
      </ScrollView>

      <View style={styles.bottomNav}>
        <NavButton label="Home" icon="⌂" active={tab === "home"} onPress={() => setTab("home")} />
        <NavButton label="Screener" icon="⌕" active={tab === "scan"} onPress={() => setTab("scan")} />
        <NavButton label="RRG" icon="◎" active={tab === "rrg"} onPress={() => setTab("rrg")} />
        <NavButton label="Research" icon="✦" active={tab === "research"} onPress={() => setTab("research")} />
        <NavButton label="Paper book" icon="▤" active={tab === "orders"} onPress={() => setTab("orders")} />
      </View>
    </SafeAreaView>
  );
}

function HomeScreen({ onTab }: { onTab: (tab: Tab) => void }) {
  const [visibleQuotes, setVisibleQuotes] = useState(quotes);
  const [feedMode, setFeedMode] = useState("DEMO");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/v1/screener/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        universe: "nifty50",
        timeframe: "1d",
        conditions: [],
        limit: 4,
      }),
      signal: controller.signal,
    })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("API unavailable"))))
      .then((data) => {
        if (!Array.isArray(data.results) || data.results.length === 0) return;
        setVisibleQuotes(data.results.map((row: { symbol: string; ltp: number; changePct: number; signal: string }) => ({
          symbol: row.symbol,
          price: `₹${Number(row.ltp).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          change: `${row.changePct >= 0 ? "+" : ""}${Number(row.changePct).toFixed(2)}%`,
          signal: row.signal || "Watch",
          color: row.changePct >= 0 ? colors.green : colors.red,
        })));
        setFeedMode(data.mode === "connected" ? "LIVE" : "DEMO");
      })
      .catch(() => setFeedMode("DEMO"));

    return () => controller.abort();
  }, []);

  return (
    <>
      <Text style={styles.eyebrow}>FRIDAY · 28 AUG 2026</Text>
      <Text style={styles.heading}>Good morning, Rahul.</Text>
      <Text style={styles.body}>Your private research workspace is ready.</Text>

      <View style={styles.cards}>
        <Metric label="Paper capital" value="₹1,00,000" detail="Available" />
        <Metric label="Today’s move" value="+₹2,480" detail="Simulated" positive />
      </View>

      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>Market pulse</Text><Text style={styles.link}>NIFTY 50 · 1D · {feedMode}</Text></View>
      <View style={styles.chartCard}>
        <Text style={styles.chartValue}>24,548.70</Text>
        <Text style={styles.positive}>+0.84% today</Text>
        <View style={styles.chart}><View style={styles.chartLine} /><View style={styles.chartLineTwo} /></View>
        <View style={styles.chartLabels}><Text>01 Aug</Text><Text>15 Aug</Text><Text>28 Aug</Text></View>
      </View>

      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>Saved momentum scan</Text><Pressable onPress={() => onTab("scan")}><Text style={styles.link}>Open →</Text></Pressable></View>
      <View style={styles.listCard}>
        {visibleQuotes.map((quote) => <QuoteRow key={quote.symbol} {...quote} />)}
      </View>

      <Pressable style={styles.primary} onPress={() => onTab("scan")}><Text style={styles.primaryText}>Run screener</Text><Text style={styles.primaryArrow}>→</Text></Pressable>
    </>
  );
}

function ScanScreen() {
  const [catalog, setCatalog] = useState<ScreenerCategory[]>(fallbackCatalog);
  const [universe, setUniverse] = useState("nifty50");
  const [timeframe, setTimeframe] = useState("1d");
  const [logic, setLogic] = useState<Logic>("all");
  const [conditions, setConditions] = useState<ConditionState[]>(defaultMobileConditions);
  const [groups, setGroups] = useState<FilterGroup[]>([]);
  const [results, setResults] = useState<DisplayQuote[]>(quotes);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [fundamentalsLoading, setFundamentalsLoading] = useState(false);
  const [feedMode, setFeedMode] = useState("DEMO");
  const [pickerTarget, setPickerTarget] = useState<PickerTarget | null>(null);
  const [eodhdStatus, setEodhdStatus] = useState<EodhdStatus>({ configured: false, defaultExchange: "NSE", message: "Checking backend configuration…" });

  const fields = catalog.flatMap((category) => category.items);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/v1/screener/catalog`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("Catalog unavailable"))))
      .then((data) => {
        if (Array.isArray(data.categories) && data.categories.length > 0) setCatalog(data.categories);
      })
      .catch(() => setCatalog(fallbackCatalog));
    fetch(`${API_URL}/api/v1/fundamentals/providers/eodhd/status`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("Provider status unavailable"))))
      .then((data) => setEodhdStatus({
        configured: Boolean(data.configured),
        defaultExchange: data.defaultExchange || "NSE",
        message: data.message || "EODHD provider status loaded.",
      }))
      .catch(() => setEodhdStatus({ configured: false, defaultExchange: "NSE", message: "Backend unavailable; EODHD status could not be checked." }));
    return () => controller.abort();
  }, []);

  function newCondition(): ConditionState {
    return { id: `condition-${Date.now()}-${Math.random().toString(16).slice(2)}`, field: "close", operator: ">", value: 0, timeframe, lookback: 0, parameters: {} };
  }

  function updateCondition(id: string, patch: Partial<ConditionState>, groupId?: string) {
    if (groupId) {
      setGroups((current) => current.map((group) => group.id === groupId ? { ...group, conditions: group.conditions.map((condition) => condition.id === id ? { ...condition, ...patch } : condition) } : group));
      return;
    }
    setConditions((current) => current.map((condition) => condition.id === id ? { ...condition, ...patch } : condition));
  }

  function removeCondition(id: string, groupId?: string) {
    if (groupId) {
      setGroups((current) => current.map((group) => group.id === groupId ? { ...group, conditions: group.conditions.filter((condition) => condition.id !== id) } : group));
      return;
    }
    setConditions((current) => current.filter((condition) => condition.id !== id));
  }

  function removeConditionsRight(id: string, groupId?: string) {
    const keepThrough = (items: ConditionState[]) => {
      const index = items.findIndex((condition) => condition.id === id);
      return index < 0 ? items : items.slice(0, index + 1);
    };
    if (groupId) {
      setGroups((current) => current.map((group) => group.id === groupId ? { ...group, conditions: keepThrough(group.conditions) } : group));
      return;
    }
    setConditions(keepThrough);
  }

  function addCondition(groupId?: string) {
    const condition = newCondition();
    if (groupId) {
      setGroups((current) => current.map((group) => group.id === groupId ? { ...group, conditions: [...group.conditions, condition] } : group));
      return;
    }
    setConditions((current) => [...current, condition]);
  }

  function addGroup() {
    setGroups((current) => [...current, { id: `group-${Date.now()}`, logic: "all", conditions: [newCondition()] }]);
  }

  function findTargetCondition(target: PickerTarget): ConditionState | undefined {
    if (target.groupId) return groups.find((group) => group.id === target.groupId)?.conditions.find((condition) => condition.id === target.conditionId);
    return conditions.find((condition) => condition.id === target.conditionId);
  }

  function selectField(definition: ScreenerField) {
    if (!pickerTarget) return;
    if (definition.kind === "group") {
      addGroup();
      setPickerTarget(null);
      return;
    }
    if (definition.kind === "measure") {
      updateCondition(pickerTarget.conditionId, { compare_field: undefined, compare_parameters: {} }, pickerTarget.groupId);
      setPickerTarget(null);
      return;
    }
    const target = findTargetCondition(pickerTarget);
    if (!target) return;
    if (pickerTarget.mode === "compare") {
      updateCondition(target.id, { compare_field: definition.id, compare_parameters: Object.fromEntries(definition.parameters.map((parameter) => [parameter.name, parameter.default])) }, pickerTarget.groupId);
    } else if (pickerTarget.mode === "compare_parameter" && pickerTarget.parameterName) {
      updateCondition(target.id, { compare_parameters: { ...(target.compare_parameters || {}), [pickerTarget.parameterName]: definition.id } }, pickerTarget.groupId);
    } else if (pickerTarget.mode === "parameter" && pickerTarget.parameterName) {
      updateCondition(target.id, { parameters: { ...target.parameters, [pickerTarget.parameterName]: definition.id } }, pickerTarget.groupId);
    } else {
      const parameters = Object.fromEntries(definition.parameters.map((parameter) => [parameter.name, parameter.default]));
      updateCondition(target.id, {
        field: definition.id,
        parameters,
        operator: definition.valueType === "string" ? "=" : ">",
        value: definition.valueType === "string" ? "" : 0,
        compare_field: undefined,
        compare_parameters: {},
      }, pickerTarget.groupId);
    }
    setPickerTarget(null);
  }

  async function runScan() {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/screener/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ universe, timeframe, logic, conditions, groups, limit: 50 }),
      });
      if (!response.ok) throw new Error("Scan unavailable");
      const data = await response.json();
      const rows = Array.isArray(data.results) ? data.results : [];
      setResults(rows.map((row: { symbol: string; ltp: number; changePct: number; signal: string }) => ({
        symbol: row.symbol,
        price: `₹${Number(row.ltp).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        change: `${row.changePct >= 0 ? "+" : ""}${Number(row.changePct).toFixed(2)}%`,
        signal: row.signal || "Watch",
        color: row.changePct >= 0 ? colors.green : colors.red,
      })));
      setWarnings(Array.isArray(data.fieldWarnings) ? data.fieldWarnings : []);
      setFeedMode(data.mode === "connected" ? "LIVE" : "DEMO");
    } catch {
      setResults(quotes);
      setWarnings(["Backend unavailable. Showing the local demo preview; start FastAPI to evaluate these rules."]);
      setFeedMode("LOCAL DEMO");
    } finally {
      setLoading(false);
    }
  }

  async function syncFundamentals() {
    if (!eodhdStatus.configured) {
      setWarnings(["Add EODHD_API_TOKEN to the backend .env file and restart FastAPI. Never place this key in EXPO_PUBLIC_ variables."]);
      return;
    }
    setFundamentalsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/fundamentals/providers/eodhd/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: fundamentalSyncSymbols, exchange: eodhdStatus.defaultExchange }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "EODHD sync failed.");
      const failures = (Array.isArray(data.results) ? data.results : [])
        .filter((item: { status: string }) => item.status === "failed")
        .map((item: { symbol: string; message: string }) => `${item.symbol}: ${item.message}`);
      setWarnings([`EODHD mapped ${data.symbolsMapped}/${data.symbolsRequested} symbols and stored ${data.valuesImported} values. Run the scan to apply them.`, data.warning, ...failures]);
    } catch (error) {
      setWarnings([error instanceof Error ? error.message : "EODHD sync failed without exposing the API token."]);
    } finally {
      setFundamentalsLoading(false);
    }
  }

  return (
    <>
      <Text style={styles.eyebrow}>RULE BUILDER</Text>
      <Text style={styles.heading}>Market screener</Text>
      <Text style={styles.body}>The same Chartink-style rule contract used by the web terminal.</Text>
      <View style={[styles.providerCard, eodhdStatus.configured && styles.providerCardReady]}>
        <View style={styles.providerCopy}><Text style={styles.providerTitle}>EODHD fundamentals</Text><Text style={styles.providerMessage}>{eodhdStatus.message}</Text></View>
        <Pressable style={styles.providerButton} onPress={syncFundamentals} disabled={fundamentalsLoading}><Text style={styles.providerButtonText}>{fundamentalsLoading ? "Syncing…" : "Sync"}</Text></Pressable>
      </View>
      <View style={styles.formCard}>
        <Text style={styles.fieldLabel}>UNIVERSE</Text>
        <ChoiceRow choices={[["nifty50", "NIFTY 50"], ["banknifty", "BANKNIFTY"], ["midcap150", "MIDCAP"], ["crypto", "CRYPTO"]]} value={universe} onChange={setUniverse} />
        <Text style={styles.fieldLabel}>BASE TIMEFRAME</Text>
        <ChoiceRow choices={[["5m", "5m"], ["15m", "15m"], ["1h", "1h"], ["1d", "1D"], ["1w", "1W"], ["1M", "1M"]]} value={timeframe} onChange={setTimeframe} />
        <View style={styles.matchRow}><Text style={styles.matchLabel}>MATCH CONDITIONS AND GROUPS</Text><LogicToggle value={logic} onChange={setLogic} /></View>
        {conditions.map((condition, index) => <MobileConditionEditor
          key={condition.id}
          index={index + 1}
          condition={condition}
          fields={fields}
          onOpen={(mode, parameterName) => setPickerTarget({ conditionId: condition.id, mode, parameterName })}
          onUpdate={(patch) => updateCondition(condition.id, patch)}
          onRemove={() => removeCondition(condition.id)}
          onRemoveRight={() => removeConditionsRight(condition.id)}
          hasFollowing={index < conditions.length - 1}
        />)}
        <Pressable style={styles.addButton} onPress={() => addCondition()}><Text style={styles.addText}>＋ Add condition</Text></Pressable>
        {groups.map((group, groupIndex) => <View style={styles.nestedGroup} key={group.id}>
          <View style={styles.groupHeader}><View><Text style={styles.groupKicker}>SUB-FILTER {groupIndex + 1}</Text><Text style={styles.groupTitle}>Nested group</Text></View><LogicToggle value={group.logic} onChange={(value) => setGroups((current) => current.map((item) => item.id === group.id ? { ...item, logic: value } : item))} /><Pressable onPress={() => setGroups((current) => current.filter((item) => item.id !== group.id))}><Text style={styles.removeText}>×</Text></Pressable></View>
          {group.conditions.map((condition, index) => <MobileConditionEditor
            key={condition.id}
            index={index + 1}
            condition={condition}
            fields={fields}
            onOpen={(mode, parameterName) => setPickerTarget({ conditionId: condition.id, groupId: group.id, mode, parameterName })}
            onUpdate={(patch) => updateCondition(condition.id, patch, group.id)}
            onRemove={() => removeCondition(condition.id, group.id)}
            onRemoveRight={() => removeConditionsRight(condition.id, group.id)}
            hasFollowing={index < group.conditions.length - 1}
          />)}
          <Pressable style={styles.addButton} onPress={() => addCondition(group.id)}><Text style={styles.addText}>＋ Add group condition</Text></Pressable>
        </View>)}
        <View style={styles.builderActions}><Pressable style={styles.secondaryCompact} onPress={addGroup}><Text style={styles.secondaryText}>＋ Nested group</Text></Pressable><Pressable style={styles.primaryCompact} onPress={runScan} disabled={loading}><Text style={styles.primaryText}>{loading ? "Running…" : "Run scan"}</Text></Pressable></View>
      </View>
      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{results.length} matches</Text><Text style={styles.link}>{feedMode} FEED</Text></View>
      <View style={styles.listCard}>{results.map((quote) => <QuoteRow key={quote.symbol} {...quote} />)}</View>
      {(warnings.length ? warnings : ["SmartAPI scans are read-only. Trade/depth fields identify the extra feed needed before live evaluation."]).map((warning) => <View style={styles.warning} key={warning}><Text style={styles.warningIcon}>!</Text><Text style={styles.warningText}>{warning}</Text></View>)}
      <FieldPickerModal visible={pickerTarget !== null} categories={catalog} target={pickerTarget} targetCondition={pickerTarget ? findTargetCondition(pickerTarget) : undefined} fields={fields} onSelect={selectField} onClose={() => setPickerTarget(null)} />
    </>
  );
}

function RrgScreen() {
  return (
    <>
      <Text style={styles.eyebrow}>RELATIVE ROTATION · 20 BARS</Text>
      <Text style={styles.heading}>RRG radar</Text>
      <Text style={styles.body}>Leadership rotation across NIFTY 50.</Text>
      <View style={styles.rrgCard}>
        <View style={[styles.quad, styles.topLeft]}><Text style={styles.quadBlue}>IMPROVING</Text></View>
        <View style={[styles.quad, styles.topRight]}><Text style={styles.quadGreen}>LEADING</Text></View>
        <View style={[styles.quad, styles.bottomLeft]}><Text style={styles.quadRed}>LAGGING</Text></View>
        <View style={[styles.quad, styles.bottomRight]}><Text style={styles.quadOrange}>WEAKENING</Text></View>
        <View style={styles.crossVertical} /><View style={styles.crossHorizontal} />
        <View style={[styles.rrgPoint, { left: "68%", top: "26%", backgroundColor: colors.green }]}><Text style={styles.pointText}>RE</Text></View>
        <View style={[styles.rrgPoint, { left: "58%", top: "34%", backgroundColor: colors.green }]}><Text style={styles.pointText}>IC</Text></View>
        <View style={[styles.rrgPoint, { left: "32%", top: "39%", backgroundColor: colors.blue }]}><Text style={styles.pointText}>BH</Text></View>
        <View style={[styles.rrgPoint, { left: "37%", top: "67%", backgroundColor: colors.red }]}><Text style={styles.pointText}>TC</Text></View>
      </View>
      <Text style={styles.sectionTitle}>Rotation table</Text>
      <View style={styles.listCard}>{["RELIANCE", "ICICIBANK", "BHARTIARTL", "TCS"].map((symbol, index) => <View style={styles.rotationRow} key={symbol}><View style={[styles.smallDot, { backgroundColor: [colors.green, colors.green, colors.blue, colors.red][index] }]} /><Text style={styles.rowSymbol}>{symbol}</Text><Text style={styles.rowValue}>{["Leading", "Leading", "Improving", "Lagging"][index]}</Text></View>)}</View>
    </>
  );
}

function ResearchScreen() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Run the shared advisory research packet.");
  const [summary, setSummary] = useState<string | null>(null);
  const [decision, setDecision] = useState<string | null>(null);
  const [risks, setRisks] = useState<string[]>([]);

  async function analyze() {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/research/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, timeframe: "1d", universe: "nifty50", include_news: true, include_fundamentals: true }),
      });
      if (!response.ok) throw new Error("API unavailable");
      const data = await response.json();
      setSummary(data.summary || "No summary returned.");
      setDecision(data.decision || "watch");
      setRisks(Array.isArray(data.risks) ? data.risks : []);
      setMessage("Evidence packet loaded; paper approval is still required.");
    } catch {
      setMessage("Backend unavailable. Start FastAPI, then try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Text style={styles.eyebrow}>ADVISORY RESEARCH · PAPER ONLY</Text>
      <Text style={styles.heading}>Research Copilot</Text>
      <Text style={styles.body}>Specialist-style analysis with evidence, uncertainty and no order authority.</Text>
      <View style={styles.formCard}>
        <Text style={styles.fieldLabel}>SYMBOL</Text>
        <TextInput style={styles.input} value={symbol} onChangeText={(value) => setSymbol(value.toUpperCase())} autoCapitalize="characters" />
        <Pressable style={styles.primary} onPress={analyze} disabled={loading}><Text style={styles.primaryText}>{loading ? "Analyzing..." : "Analyze symbol"}</Text><Text style={styles.primaryArrow}>→</Text></Pressable>
      </View>
      {summary && <View style={styles.orderCard}><Text style={styles.orderLabel}>RESEARCH STATE · {String(decision).replace("_", " ").toUpperCase()}</Text><Text style={styles.orderTitle}>{summary}</Text><Text style={styles.warningText}>Manual approval required · agents cannot place orders.</Text>{risks.map((risk) => <Text style={[styles.rowSub, { marginTop: 9 }]} key={risk}>• {risk}</Text>)}</View>}
      <View style={styles.warning}><Text style={styles.warningIcon}>!</Text><Text style={styles.warningText}>{message}</Text></View>
    </>
  );
}

function OrdersScreen() {
  return (
    <>
      <Text style={styles.eyebrow}>PAPER LEDGER</Text>
      <Text style={styles.heading}>Order review</Text>
      <Text style={styles.body}>Every trade remains simulated until live execution is explicitly enabled.</Text>
      <View style={styles.orderCard}><Text style={styles.orderLabel}>RELIANCE · MIS</Text><Text style={styles.orderTitle}>Buy 10 shares at ₹2,942.40</Text><View style={styles.orderGrid}><Field label="Margin" value="₹5,884.80" /><Field label="Charges est." value="₹18.42" /></View><View style={styles.orderButtons}><Pressable style={styles.secondary}><Text style={styles.secondaryText}>Edit</Text></Pressable><Pressable style={styles.primarySmall}><Text style={styles.primaryText}>Paper order</Text></Pressable></View></View>
      <View style={styles.warning}><Text style={styles.warningIcon}>✓</Text><Text style={styles.warningText}>Live trading is disabled. Broker calculations will be verified before any execution adapter is added.</Text></View>
    </>
  );
}

function Metric({ label, value, detail, positive }: { label: string; value: string; detail: string; positive?: boolean }) {
  return <View style={styles.metric}><Text style={styles.metricLabel}>{label}</Text><Text style={[styles.metricValue, positive && styles.positive]}>{value}</Text><Text style={styles.metricDetail}>{detail}</Text></View>;
}

function QuoteRow({ symbol, price, change, signal, color }: { symbol: string; price: string; change: string; signal: string; color: string }) {
  return <View style={styles.quoteRow}><View style={[styles.symbolIcon, { backgroundColor: color + "22" }]}><Text style={[styles.symbolIconText, { color }]}>{symbol.slice(0, 2)}</Text></View><View style={styles.quoteName}><Text style={styles.rowSymbol}>{symbol}</Text><Text style={styles.rowSub}>{signal}</Text></View><View><Text style={styles.rowPrice}>{price}</Text><Text style={[styles.rowValue, { color }]}>{change}</Text></View></View>;
}

function Field({ label, value }: { label: string; value: string }) {
  return <View style={styles.field}><Text style={styles.fieldLabel}>{label}</Text><View style={styles.fieldValue}><Text style={styles.fieldText}>{value}</Text><Text style={styles.chevron}>⌄</Text></View></View>;
}

function ChoiceRow({ choices, value, onChange }: { choices: Array<[string, string]>; value: string; onChange: (value: string) => void }) {
  return <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.choiceRow}>{choices.map(([key, label]) => <Pressable style={[styles.choiceChip, value === key && styles.choiceChipActive]} onPress={() => onChange(key)} key={key}><Text style={[styles.choiceText, value === key && styles.choiceTextActive]}>{label}</Text></Pressable>)}</ScrollView>;
}

function LogicToggle({ value, onChange }: { value: Logic; onChange: (value: Logic) => void }) {
  return <View style={styles.logicToggle}><Pressable style={[styles.logicChip, value === "all" && styles.logicChipActive]} onPress={() => onChange("all")}><Text style={[styles.logicText, value === "all" && styles.logicTextActive]}>ALL</Text></Pressable><Pressable style={[styles.logicChip, value === "any" && styles.logicChipActive]} onPress={() => onChange("any")}><Text style={[styles.logicText, value === "any" && styles.logicTextActive]}>ANY</Text></Pressable></View>;
}

function MobileConditionEditor({ index, condition, fields, onOpen, onUpdate, onRemove, onRemoveRight, hasFollowing }: {
  index: number;
  condition: ConditionState;
  fields: ScreenerField[];
  onOpen: (mode: PickerTarget["mode"], parameterName?: string) => void;
  onUpdate: (patch: Partial<ConditionState>) => void;
  onRemove: () => void;
  onRemoveRight: () => void;
  hasFollowing: boolean;
}) {
  const definition = fields.find((item) => item.id === condition.field) || fieldDefinition(condition.field, condition.field, "stock_attributes");
  const numberOperators: Operator[] = [">", "<", ">=", "<=", "=", "!=", "crosses_above", "crosses_below"];
  const stringOperators: Operator[] = ["=", "!=", "contains", "not_contains", "starts_with", "ends_with"];
  const operators = definition.valueType === "string" ? stringOperators : numberOperators;
  const comparable = fields.filter((item) => item.kind !== "measure" && item.kind !== "group" && item.valueType === definition.valueType);
  const compareDefinition = fields.find((item) => item.id === condition.compare_field);
  const timeframes = ["5m", "15m", "1h", "4h", "1d", "1w", "1M", "1Y"];

  function cycle<T>(items: T[], current: T): T {
    const index = items.indexOf(current);
    return items[(index + 1) % items.length];
  }

  function updateParameter(parameter: FieldParameter, value: string | number) {
    onUpdate({ parameters: { ...condition.parameters, [parameter.name]: value } });
  }

  function updateCompareParameter(parameter: FieldParameter, value: string | number) {
    onUpdate({ compare_parameters: { ...(condition.compare_parameters || {}), [parameter.name]: value } });
  }

  return <View style={styles.mobileConditionCard}>
    <View style={styles.mobileConditionHeader}>
      <Text style={styles.conditionNumber}>{String(index).padStart(2, "0")}</Text>
      <Pressable style={styles.mobileFieldButton} onPress={() => onOpen("primary")}><Text style={styles.mobileFieldName} numberOfLines={1}>{definition.label}</Text><Text style={styles.mobileFieldCategory}>{definition.category.replaceAll("_", " ")}</Text></Pressable>
      <Pressable onPress={onRemove}><Text style={styles.removeText}>×</Text></Pressable>
    </View>
    <View style={styles.mobileRuleRow}>
      <Pressable style={styles.ruleChip} onPress={() => onUpdate({ operator: cycle(operators, condition.operator) })}><Text style={styles.ruleChipLabel}>OPERATOR</Text><Text style={styles.ruleChipValue}>{operatorLabels[condition.operator]}</Text></Pressable>
      <Pressable style={styles.ruleChip} onPress={() => { const first = comparable[0]; onUpdate(condition.compare_field ? { compare_field: undefined, compare_parameters: {} } : { compare_field: first?.id || "close", compare_parameters: Object.fromEntries((first?.parameters || []).map((parameter) => [parameter.name, parameter.default])) }); }}><Text style={styles.ruleChipLabel}>COMPARE</Text><Text style={styles.ruleChipValue}>{condition.compare_field ? "Field" : "Number"}</Text></Pressable>
      <Pressable style={styles.ruleChip} onPress={() => onUpdate({ timeframe: cycle(timeframes, condition.timeframe) })}><Text style={styles.ruleChipLabel}>INTERVAL</Text><Text style={styles.ruleChipValue}>{condition.timeframe}</Text></Pressable>
    </View>
    {condition.compare_field ? <Pressable style={styles.compareFieldButton} onPress={() => onOpen("compare")}><Text style={styles.ruleChipLabel}>COMPARISON FIELD</Text><Text style={styles.compareFieldText}>{compareDefinition?.label || condition.compare_field}  ›</Text></Pressable> : <View><Text style={styles.ruleChipLabel}>VALUE</Text><TextInput style={styles.conditionInput} value={String(condition.value)} keyboardType={definition.valueType === "number" ? "decimal-pad" : "default"} onChangeText={(value) => onUpdate({ value: definition.valueType === "number" ? Number(value || 0) : value })} /></View>}
    <View style={styles.parameterWrap}>
      {definition.parameters.map((parameter) => {
        const parameterValue = condition.parameters[parameter.name] ?? parameter.default;
        if (parameter.type === "field") {
          const selected = fields.find((item) => item.id === parameterValue);
          return <Pressable style={styles.parameterMobile} onPress={() => onOpen("parameter", parameter.name)} key={parameter.name}><Text style={styles.ruleChipLabel}>{parameter.label.toUpperCase()}</Text><Text style={styles.parameterValue}>{selected?.label || String(parameterValue)}  ›</Text></Pressable>;
        }
        if (parameter.type === "select") {
          const options = parameter.options || [];
          return <Pressable style={styles.parameterMobile} onPress={() => updateParameter(parameter, cycle(options, String(parameterValue)))} key={parameter.name}><Text style={styles.ruleChipLabel}>{parameter.label.toUpperCase()}</Text><Text style={styles.parameterValue}>{String(parameterValue)}</Text></Pressable>;
        }
        return <View style={styles.parameterMobile} key={parameter.name}><Text style={styles.ruleChipLabel}>{parameter.label.toUpperCase()}</Text><TextInput style={styles.parameterInput} value={String(parameterValue)} keyboardType={parameter.type === "number" ? "decimal-pad" : "default"} onChangeText={(value) => updateParameter(parameter, parameter.type === "number" ? Number(value || 0) : value)} /></View>;
      })}
      {compareDefinition?.parameters.map((parameter) => {
        const parameterValue = condition.compare_parameters?.[parameter.name] ?? parameter.default;
        if (parameter.type === "field") {
          const selected = fields.find((item) => item.id === parameterValue);
          return <Pressable style={styles.parameterMobile} onPress={() => onOpen("compare_parameter", parameter.name)} key={`compare-${parameter.name}`}><Text style={styles.ruleChipLabel}>COMPARE {parameter.label.toUpperCase()}</Text><Text style={styles.parameterValue}>{selected?.label || String(parameterValue)}  ›</Text></Pressable>;
        }
        if (parameter.type === "select") {
          const options = parameter.options || [];
          return <Pressable style={styles.parameterMobile} onPress={() => updateCompareParameter(parameter, cycle(options, String(parameterValue)))} key={`compare-${parameter.name}`}><Text style={styles.ruleChipLabel}>COMPARE {parameter.label.toUpperCase()}</Text><Text style={styles.parameterValue}>{String(parameterValue)}</Text></Pressable>;
        }
        return <View style={styles.parameterMobile} key={`compare-${parameter.name}`}><Text style={styles.ruleChipLabel}>COMPARE {parameter.label.toUpperCase()}</Text><TextInput style={styles.parameterInput} value={String(parameterValue)} keyboardType={parameter.type === "number" ? "decimal-pad" : "default"} onChangeText={(value) => updateCompareParameter(parameter, parameter.type === "number" ? Number(value || 0) : value)} /></View>;
      })}
      <View style={styles.parameterMobile}><Text style={styles.ruleChipLabel}>BARS AGO</Text><TextInput style={styles.parameterInput} value={String(condition.lookback)} keyboardType="number-pad" onChangeText={(value) => onUpdate({ lookback: Math.max(0, Number(value || 0)) })} /></View>
    </View>
    <View style={styles.conditionFooter}>
      {definition.availability !== "ready" && <Text style={styles.availabilityBadge}>{availabilityLabel(definition.availability)}</Text>}
      <Pressable style={[styles.removeRightButton, !hasFollowing && styles.removeRightDisabled]} onPress={onRemoveRight} disabled={!hasFollowing}><Text style={styles.removeRightText}>Remove all on right</Text></Pressable>
    </View>
  </View>;
}

function FieldPickerModal({ visible, categories, target, targetCondition, fields, onSelect, onClose }: {
  visible: boolean;
  categories: ScreenerCategory[];
  target: PickerTarget | null;
  targetCondition?: ConditionState;
  fields: ScreenerField[];
  onSelect: (field: ScreenerField) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (visible) setQuery("");
  }, [visible]);
  const sourceDefinition = fields.find((item) => item.id === targetCondition?.field);
  const normalized = query.trim().toLowerCase();

  function allowed(item: ScreenerField): boolean {
    if (target?.mode === "parameter" || target?.mode === "compare_parameter") return item.kind === "field" && item.valueType === "number";
    if (target?.mode === "compare") return item.kind === "measure" || (item.kind !== "group" && item.valueType === sourceDefinition?.valueType);
    return true;
  }

  const sections = categories
    .map((category) => ({
      id: category.id,
      title: category.label,
      data: category.items.filter((item) => allowed(item) && (!normalized || `${item.label} ${item.id} ${category.label}`.toLowerCase().includes(normalized))),
    }))
    .filter((section) => section.data.length > 0);

  return <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
    <SafeAreaView style={styles.pickerSafe}>
      <View style={styles.pickerHeader}><View><Text style={styles.pickerEyebrow}>{target?.mode === "compare" ? "SELECT COMPARISON" : target?.mode === "parameter" || target?.mode === "compare_parameter" ? "SELECT INPUT FIELD" : "INDICATORS & FORMULAS"}</Text><Text style={styles.pickerTitle}>Choose a screener field</Text></View><Pressable style={styles.pickerClose} onPress={onClose}><Text style={styles.removeText}>×</Text></Pressable></View>
      <TextInput style={styles.pickerSearch} placeholder="Search fields, indicators or functions" placeholderTextColor={colors.muted} value={query} onChangeText={setQuery} autoFocus />
      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.pickerContent}
        initialNumToRender={24}
        maxToRenderPerBatch={24}
        windowSize={7}
        stickySectionHeadersEnabled
        renderSectionHeader={({ section }) => <View style={styles.pickerCategory}><Text style={styles.pickerCategoryTitle}>{section.title}</Text></View>}
        renderItem={({ item }) => <Pressable style={styles.pickerItem} onPress={() => onSelect(item)}><Text style={styles.pickerStar}>☆</Text><View style={styles.pickerItemCopy}><Text style={styles.pickerItemTitle}>{item.label}</Text>{item.description ? <Text style={styles.pickerItemDescription}>{item.description}</Text> : null}</View>{item.availability !== "ready" && <Text style={styles.pickerBadge}>{availabilityLabel(item.availability)}</Text>}</Pressable>}
      />
    </SafeAreaView>
  </Modal>;
}

function NavButton({ label, icon, active, onPress }: { label: string; icon: string; active: boolean; onPress: () => void }) {
  return <Pressable style={styles.navButton} onPress={onPress}><Text style={[styles.navIcon, active && styles.navActive]}>{icon}</Text><Text style={[styles.navLabel, active && styles.navActive]}>{label}</Text></Pressable>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { height: 70, paddingHorizontal: 18, flexDirection: "row", alignItems: "center", borderBottomWidth: 1, borderBottomColor: colors.line },
  logo: { width: 33, height: 33, borderRadius: 10, backgroundColor: colors.blue, alignItems: "center", justifyContent: "center" },
  logoText: { color: colors.bg, fontSize: 20, fontWeight: "800" },
  headerTitle: { marginLeft: 10 },
  title: { color: colors.text, fontSize: 11, fontWeight: "800", letterSpacing: 2 },
  subtitle: { color: colors.muted, fontSize: 8, letterSpacing: 2, marginTop: 3 },
  mode: { marginLeft: "auto", flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#12382f", paddingHorizontal: 9, paddingVertical: 6, borderRadius: 12 },
  dot: { width: 6, height: 6, borderRadius: 4, backgroundColor: colors.green },
  modeText: { color: colors.green, fontSize: 9, fontWeight: "700" },
  content: { padding: 20, paddingBottom: 35 },
  input: { color: colors.text, backgroundColor: "#0a1727", borderColor: "#27415c", borderWidth: 1, borderRadius: 6, padding: 10, marginBottom: 12 },
  eyebrow: { color: "#6f88a5", fontSize: 9, letterSpacing: 1.5, fontWeight: "700", marginTop: 8 },
  heading: { color: colors.text, fontSize: 28, fontWeight: "700", marginTop: 7, letterSpacing: -0.7 },
  body: { color: colors.muted, fontSize: 12, lineHeight: 19, marginTop: 6, marginBottom: 22 },
  cards: { flexDirection: "row", gap: 9, marginBottom: 25 },
  metric: { flex: 1, backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 14 },
  metricLabel: { color: colors.muted, fontSize: 10 },
  metricValue: { color: colors.text, fontWeight: "700", fontSize: 18, marginTop: 7 },
  metricDetail: { color: "#5e7897", fontSize: 9, marginTop: 5 },
  positive: { color: colors.green },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10, marginTop: 5 },
  sectionTitle: { color: colors.text, fontSize: 15, fontWeight: "600", marginBottom: 10 },
  link: { color: colors.blue, fontSize: 10 },
  chartCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 16, marginBottom: 24 },
  chartValue: { color: colors.text, fontSize: 24, fontWeight: "700" },
  chart: { height: 125, marginTop: 15, overflow: "hidden", position: "relative", borderBottomWidth: 1, borderBottomColor: colors.line },
  chartLine: { position: "absolute", left: -15, top: 50, width: 390, height: 100, borderTopWidth: 3, borderTopColor: colors.blue, transform: [{ rotate: "-12deg" }] },
  chartLineTwo: { position: "absolute", left: -15, top: 78, width: 390, height: 100, borderTopWidth: 2, borderTopColor: colors.purple, transform: [{ rotate: "-8deg" }] },
  chartLabels: { flexDirection: "row", justifyContent: "space-between", marginTop: 7 },
  chartLabelsText: { color: colors.muted, fontSize: 9 },
  listCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, paddingHorizontal: 14, marginBottom: 18 },
  quoteRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#16283d" },
  symbolIcon: { width: 31, height: 31, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  symbolIconText: { fontSize: 9, fontWeight: "800" },
  quoteName: { flex: 1, marginLeft: 10 },
  rowSymbol: { color: "#d2e1ef", fontSize: 11, fontWeight: "600" },
  rowSub: { color: colors.muted, fontSize: 9, marginTop: 4 },
  rowPrice: { color: "#c8d8e8", fontSize: 10, textAlign: "right" },
  rowValue: { fontSize: 9, marginTop: 4, textAlign: "right" },
  primary: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: colors.blue, padding: 13, borderRadius: 8 },
  primarySmall: { flex: 1, alignItems: "center", backgroundColor: colors.blue, padding: 12, borderRadius: 8 },
  primaryText: { color: colors.bg, fontSize: 11, fontWeight: "700" },
  primaryArrow: { color: colors.bg, fontSize: 17 },
  formCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 15, marginBottom: 23 },
  field: { marginBottom: 12, flex: 1 },
  fieldLabel: { color: colors.muted, fontSize: 9, marginBottom: 6 },
  fieldValue: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#0a1727", borderColor: "#27415c", borderWidth: 1, borderRadius: 6, padding: 10 },
  fieldText: { color: "#c8d9eb", fontSize: 10 },
  chevron: { color: colors.muted, fontSize: 13 },
  choiceRow: { gap: 6, paddingBottom: 12 },
  choiceChip: { borderColor: "#2b4661", borderWidth: 1, borderRadius: 12, backgroundColor: "#0a1727", paddingHorizontal: 10, paddingVertical: 7 },
  choiceChipActive: { borderColor: "#427daf", backgroundColor: "#153854" },
  choiceText: { color: colors.muted, fontSize: 8, fontWeight: "700" },
  choiceTextActive: { color: "#a9d5ff" },
  matchLabel: { color: "#6f88a5", fontSize: 9, letterSpacing: 1, marginTop: 5, marginBottom: 5 },
  matchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 6 },
  logicToggle: { flexDirection: "row", gap: 3 },
  logicChip: { borderColor: "#29435d", borderWidth: 1, borderRadius: 5, backgroundColor: "#0a1727", paddingHorizontal: 8, paddingVertical: 5 },
  logicChipActive: { borderColor: "#437dad", backgroundColor: "#153854" },
  logicText: { color: colors.muted, fontSize: 7, fontWeight: "700" },
  logicTextActive: { color: "#a9d5ff" },
  condition: { flexDirection: "row", alignItems: "center", backgroundColor: "#102238", borderRadius: 6, padding: 11, marginTop: 6, gap: 7 },
  conditionNumber: { color: colors.blue, fontSize: 12 },
  conditionField: { flex: 1, color: "#c9daeb", fontSize: 10 },
  conditionOperator: { color: colors.purple, fontWeight: "700", fontSize: 11 },
  conditionValue: { color: colors.text, fontSize: 10, fontWeight: "600" },
  mobileConditionCard: { borderColor: "#203c58", borderWidth: 1, borderRadius: 8, backgroundColor: "#0b1b2d", padding: 9, marginTop: 7 },
  mobileConditionHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  mobileFieldButton: { flex: 1, minWidth: 0 },
  mobileFieldName: { color: "#d2e0ef", fontSize: 10, fontWeight: "600" },
  mobileFieldCategory: { color: "#607d99", fontSize: 7, marginTop: 3, textTransform: "capitalize" },
  removeText: { color: colors.red, fontSize: 22, lineHeight: 24 },
  mobileRuleRow: { flexDirection: "row", gap: 5, marginTop: 9 },
  ruleChip: { flex: 1, borderColor: "#29435d", borderWidth: 1, borderRadius: 6, backgroundColor: "#091725", padding: 7 },
  ruleChipLabel: { color: "#607d99", fontSize: 6, fontWeight: "700", letterSpacing: .5 },
  ruleChipValue: { color: "#c4d7e9", fontSize: 8, fontWeight: "600", marginTop: 4, textTransform: "capitalize" },
  conditionInput: { color: colors.text, borderColor: "#29435d", borderWidth: 1, borderRadius: 6, backgroundColor: "#091725", paddingHorizontal: 9, paddingVertical: 8, marginTop: 4, fontSize: 10 },
  compareFieldButton: { borderColor: "#29435d", borderWidth: 1, borderRadius: 6, backgroundColor: "#091725", padding: 8, marginTop: 7 },
  compareFieldText: { color: colors.blue, fontSize: 9, marginTop: 4 },
  parameterWrap: { flexDirection: "row", flexWrap: "wrap", gap: 5, marginTop: 7 },
  parameterMobile: { minWidth: 75, flexGrow: 1, borderColor: "#223d57", borderWidth: 1, borderRadius: 6, backgroundColor: "#0a1727", padding: 7 },
  parameterValue: { color: "#bcd0e3", fontSize: 8, marginTop: 4 },
  parameterInput: { color: "#cbdbea", minWidth: 45, padding: 0, marginTop: 4, fontSize: 9 },
  conditionFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 6, marginTop: 7 },
  availabilityBadge: { alignSelf: "flex-start", color: "#efb578", borderColor: "#674a31", borderWidth: 1, borderRadius: 9, backgroundColor: "#39291e", paddingHorizontal: 7, paddingVertical: 4, fontSize: 7 },
  removeRightButton: { marginLeft: "auto", borderColor: "#3a5068", borderWidth: 1, borderRadius: 9, backgroundColor: "#102238", paddingHorizontal: 8, paddingVertical: 5 },
  removeRightDisabled: { opacity: .35 },
  removeRightText: { color: "#a9bdd1", fontSize: 7 },
  addButton: { alignItems: "center", borderColor: "#315575", borderWidth: 1, borderStyle: "dashed", borderRadius: 6, padding: 10, marginTop: 10 },
  addText: { color: colors.blue, fontSize: 10 },
  nestedGroup: { borderColor: "#31506c", borderWidth: 1, borderRadius: 9, backgroundColor: "#10243a", padding: 9, marginTop: 12 },
  groupHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  groupKicker: { color: colors.purple, fontSize: 7, fontWeight: "700", letterSpacing: .6 },
  groupTitle: { color: "#c9daea", fontSize: 10, marginTop: 3 },
  builderActions: { flexDirection: "row", gap: 7, marginTop: 12 },
  secondaryCompact: { flex: 1, alignItems: "center", justifyContent: "center", borderColor: "#31506c", borderWidth: 1, borderRadius: 7, padding: 11 },
  primaryCompact: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.blue, borderRadius: 7, padding: 11 },
  warning: { flexDirection: "row", gap: 9, backgroundColor: "#2b241b", borderColor: "#5a472a", borderWidth: 1, borderRadius: 7, padding: 11, marginTop: 8 },
  warningIcon: { color: colors.orange, fontWeight: "800", fontSize: 14 },
  warningText: { flex: 1, color: "#c5a875", fontSize: 9, lineHeight: 15 },
  providerCard: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#2b241b", borderColor: "#5a472a", borderWidth: 1, borderRadius: 9, padding: 12, marginBottom: 12 },
  providerCardReady: { backgroundColor: "#12352f", borderColor: "#28634f" },
  providerCopy: { flex: 1 },
  providerTitle: { color: colors.text, fontSize: 11, fontWeight: "700" },
  providerMessage: { color: colors.muted, fontSize: 8, lineHeight: 12, marginTop: 3 },
  providerButton: { alignItems: "center", justifyContent: "center", borderColor: "#396280", borderWidth: 1, borderRadius: 7, backgroundColor: "#102a43", paddingHorizontal: 13, paddingVertical: 9 },
  providerButtonText: { color: colors.blue, fontSize: 9, fontWeight: "700" },
  rrgCard: { height: 350, borderWidth: 1, borderColor: colors.line, borderRadius: 11, backgroundColor: colors.panel, position: "relative", overflow: "hidden", marginBottom: 23 },
  quad: { position: "absolute", width: "50%", height: "50%", padding: 13 },
  topLeft: { left: 0, top: 0, backgroundColor: "#102840" },
  topRight: { right: 0, top: 0, backgroundColor: "#12352f" },
  bottomLeft: { left: 0, bottom: 0, backgroundColor: "#321d29" },
  bottomRight: { right: 0, bottom: 0, backgroundColor: "#3a2b20" },
  quadBlue: { color: colors.blue, fontSize: 8, fontWeight: "700" },
  quadGreen: { color: colors.green, fontSize: 8, fontWeight: "700", textAlign: "right" },
  quadRed: { color: colors.red, fontSize: 8, fontWeight: "700" },
  quadOrange: { color: colors.orange, fontSize: 8, fontWeight: "700", textAlign: "right" },
  crossVertical: { position: "absolute", top: 0, bottom: 0, left: "50%", borderLeftWidth: 1, borderStyle: "dashed", borderColor: "#58718b" },
  crossHorizontal: { position: "absolute", left: 0, right: 0, top: "50%", borderTopWidth: 1, borderStyle: "dashed", borderColor: "#58718b" },
  rrgPoint: { position: "absolute", width: 27, height: 27, borderRadius: 18, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: "#dcefff" },
  pointText: { color: colors.bg, fontSize: 8, fontWeight: "800" },
  rotationRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#16283d" },
  smallDot: { width: 7, height: 7, borderRadius: 5, marginRight: 10 },
  orderCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 16, marginTop: 6, marginBottom: 18 },
  orderLabel: { color: colors.blue, fontSize: 9, letterSpacing: 1.2, fontWeight: "700" },
  orderTitle: { color: colors.text, fontSize: 16, fontWeight: "600", marginTop: 9, marginBottom: 18 },
  orderGrid: { flexDirection: "row", gap: 10 },
  orderButtons: { flexDirection: "row", gap: 8, marginTop: 8 },
  secondary: { flex: 1, alignItems: "center", borderColor: "#29445f", borderWidth: 1, padding: 11, borderRadius: 8 },
  secondaryText: { color: "#b5cce2", fontSize: 11 },
  pickerSafe: { flex: 1, backgroundColor: colors.bg },
  pickerHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomColor: colors.line, borderBottomWidth: 1, paddingHorizontal: 18, paddingVertical: 14 },
  pickerEyebrow: { color: colors.purple, fontSize: 8, fontWeight: "700", letterSpacing: 1 },
  pickerTitle: { color: colors.text, fontSize: 18, fontWeight: "700", marginTop: 4 },
  pickerClose: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },
  pickerSearch: { color: colors.text, borderColor: "#2b4661", borderWidth: 1, borderRadius: 8, backgroundColor: "#0a1727", padding: 11, marginHorizontal: 16, marginVertical: 12, fontSize: 11 },
  pickerContent: { paddingHorizontal: 16, paddingBottom: 30 },
  pickerCategory: { borderColor: colors.line, borderWidth: 1, borderRadius: 9, backgroundColor: colors.panel, overflow: "hidden", marginBottom: 10 },
  pickerCategoryTitle: { color: "#6f8ba7", backgroundColor: "#10233a", paddingHorizontal: 12, paddingVertical: 9, fontSize: 8, fontWeight: "700" },
  pickerItem: { flexDirection: "row", alignItems: "center", gap: 8, borderBottomColor: "#182d44", borderBottomWidth: 1, paddingHorizontal: 11, paddingVertical: 11 },
  pickerStar: { color: "#6f86a0", fontSize: 16 },
  pickerItemCopy: { flex: 1 },
  pickerItemTitle: { color: "#d0deec", fontSize: 10, fontWeight: "600" },
  pickerItemDescription: { color: colors.muted, fontSize: 8, lineHeight: 12, marginTop: 3 },
  pickerBadge: { color: "#efb578", borderColor: "#674a31", borderWidth: 1, borderRadius: 8, paddingHorizontal: 6, paddingVertical: 3, fontSize: 6, fontWeight: "700" },
  bottomNav: { height: 73, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: "#091523", flexDirection: "row", justifyContent: "space-around", alignItems: "center" },
  navButton: { alignItems: "center", padding: 6, minWidth: 64 },
  navIcon: { color: colors.muted, fontSize: 21, lineHeight: 24 },
  navLabel: { color: colors.muted, fontSize: 9, marginTop: 4 },
  navActive: { color: colors.blue },
});
