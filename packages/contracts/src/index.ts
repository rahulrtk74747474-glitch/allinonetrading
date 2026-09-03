export type Timeframe = "5m" | "15m" | "1h" | "4h" | "1d" | "1w" | "1M" | "1Y";

export type UniverseKey =
  | "nifty50"
  | "banknifty"
  | "midcap150"
  | "custom"
  | "crypto";

export type Quadrant = "leading" | "weakening" | "lagging" | "improving";

export type ScreenerLogic = "all" | "any";

export type ScreenerOperator =
  | ">"
  | "<"
  | ">="
  | "<="
  | "="
  | "!="
  | "contains"
  | "not_contains"
  | "starts_with"
  | "ends_with"
  | "crosses_above"
  | "crosses_below";

export type ScreenerFieldAvailability =
  | "ready"
  | "metadata_required"
  | "tick_feed_required"
  | "depth_feed_required"
  | "depth_history_required"
  | "fundamentals_required"
  | "shareholding_required"
  | "cashflow_required";

export interface ScreenerFieldParameter {
  name: string;
  label: string;
  type: "number" | "text" | "select" | "field";
  default: number | string;
  min?: number;
  max?: number;
  options?: string[];
}

export interface ScreenerFieldDefinition {
  id: string;
  label: string;
  category: string;
  kind: "field" | "function" | "indicator" | "measure" | "group";
  valueType: "number" | "string" | "group";
  description: string;
  availability: ScreenerFieldAvailability;
  parameters: ScreenerFieldParameter[];
  unit?: string;
  historyMode?: "latest_snapshot";
  dataSource?: "fundamentals_import";
}

export interface ScreenerCategory {
  id: string;
  label: string;
  items: ScreenerFieldDefinition[];
}

export interface ScreenerCondition {
  id: string;
  field: string;
  operator: ScreenerOperator;
  value: number | string;
  lookback?: number;
  timeframe?: Timeframe;
  parameters?: Record<string, number | string | boolean>;
  compare_field?: string;
  compare_parameters?: Record<string, number | string | boolean>;
}

export interface ScreenerFilterGroup {
  id: string;
  logic: ScreenerLogic;
  conditions: ScreenerCondition[];
}

export interface ScreenerRequest {
  universe: UniverseKey;
  timeframe: Timeframe;
  logic?: ScreenerLogic;
  conditions: ScreenerCondition[];
  groups?: ScreenerFilterGroup[];
  limit?: number;
}

export interface ScreenerResult {
  symbol: string;
  exchange: string;
  sector: string;
  ltp: number;
  changePct: number;
  volume: number;
  signal: string;
  score: number;
  metrics?: Record<string, number | string | null>;
}

export interface FundamentalImportRow {
  symbol: string;
  as_of: string;
  source: string;
  values: Record<string, number | null>;
}

export interface FundamentalImportRequest {
  rows: FundamentalImportRow[];
}

export interface FundamentalDataStatus {
  configured: boolean;
  symbols: number;
  values: number;
  latestAsOf: string | null;
  sources: string[];
}

export interface EodhdProviderStatus {
  provider: "EODHD";
  configured: boolean;
  apiVersion: "v1.1";
  defaultExchange: string;
  maxSymbolsPerSync: number;
  credentialLocation: "backend environment only";
  coverage: string[];
  limitations: string[];
  message: string;
}

export interface EodhdSyncRequest {
  symbols: string[];
  exchange?: string;
}

export interface EodhdSyncSymbolResult {
  symbol: string;
  ticker?: string;
  status: "mapped" | "failed";
  asOf?: string;
  currency?: string | null;
  fieldsMapped?: number;
  currencyAmountsSkipped?: boolean;
  message?: string;
}

export interface EodhdSyncResult {
  provider: "EODHD";
  exchange: string;
  symbolsRequested: number;
  symbolsMapped: number;
  symbolsFailed: number;
  valuesImported: number;
  staleValuesIgnored: number;
  results: EodhdSyncSymbolResult[];
  storeStatus: FundamentalDataStatus;
  warning: string;
}

export interface RrgTrailPoint {
  x: number;
  y: number;
}

export interface RrgPoint {
  symbol: string;
  sector: string;
  rsRatio: number;
  rsMomentum: number;
  quadrant: Quadrant;
  trail: RrgTrailPoint[];
}

export interface BacktestRequest {
  symbol: string;
  timeframe: Timeframe;
  initialCapital: number;
  strategyName: string;
  parameters: Record<string, number>;
}

export interface OrderPreviewRequest {
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  product: "CNC" | "MIS" | "NRML";
}

export interface OrderPreview {
  mode: "paper";
  estimatedMargin: number;
  brokerage: number;
  taxesAndCharges: number;
  totalCashImpact: number;
  breakeven: number;
}

export interface ApiStatus {
  appMode: "demo" | "connected";
  paperTrading: boolean;
  liveTrading: boolean;
  broker: string;
  fundamentals?: FundamentalDataStatus;
  fundamentalProviders?: { eodhd: EodhdProviderStatus };
}


export type ResearchDecision = "watch" | "paper_candidate" | "no_trade";
export type ResearchEvidenceStatus = "demo" | "available" | "not_loaded";

export interface ResearchRequest {
  symbol: string;
  timeframe: Timeframe;
  universe: string;
  include_news?: boolean;
  include_fundamentals?: boolean;
}

export interface ResearchEvidence {
  id: string;
  role: string;
  source: string;
  as_of: string;
  status: ResearchEvidenceStatus;
  summary: string;
  values: Record<string, number | string | null>;
}

export interface ResearchFinding {
  role: string;
  title: string;
  conclusion: string;
  confidence: number;
  evidence_ids: string[];
}

export interface ResearchReport {
  report_id: string;
  symbol: string;
  timeframe: Timeframe;
  universe: string;
  mode: "demo" | "paper" | "connected";
  data_quality: ResearchEvidenceStatus;
  as_of: string;
  decision: ResearchDecision;
  confidence: number;
  summary: string;
  findings: ResearchFinding[];
  evidence: ResearchEvidence[];
  risks: string[];
  next_actions: string[];
  agent_trace: string[];
  order_authority: "none";
  approval_required: boolean;
  warnings: string[];
}
