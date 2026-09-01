export type Timeframe = "5m" | "15m" | "1h" | "4h" | "1d" | "1w" | "1M" | "1Y";

export type UniverseKey =
  | "nifty50"
  | "banknifty"
  | "midcap150"
  | "custom"
  | "crypto";

export type Quadrant = "leading" | "weakening" | "lagging" | "improving";

export interface ScreenerCondition {
  id: string;
  field: string;
  operator: ">" | "<" | ">=" | "<=" | "=" | "crosses_above" | "crosses_below";
  value: number | string;
  lookback?: number;
  timeframe?: Timeframe;
}

export interface ScreenerRequest {
  universe: UniverseKey;
  timeframe: Timeframe;
  conditions: ScreenerCondition[];
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
