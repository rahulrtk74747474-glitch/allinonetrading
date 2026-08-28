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
