from __future__ import annotations

import math
import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from .brokers.angel_one import AngelOneAdapter
from .research.models import ResearchRequest
from .research.service import build_research_report
from .screener import catalog_response, request_field_warnings, scan_rows


def cors_origins() -> list[str]:
    configured = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="All In One Trading API",
    version="0.1.0",
    description="Private research, screening and paper-trading API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


Timeframe = Literal["5m", "15m", "1h", "4h", "1d", "1w", "1M", "1Y"]
Operator = Literal[
    ">",
    "<",
    ">=",
    "<=",
    "=",
    "!=",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "crosses_above",
    "crosses_below",
]
Logic = Literal["all", "any"]


class Condition(BaseModel):
    id: str
    field: str
    operator: Operator
    value: float | str = 0
    lookback: int = Field(default=0, ge=0)
    timeframe: Timeframe = "1d"
    parameters: dict[str, float | str | bool] = Field(default_factory=dict)
    compare_field: str | None = None
    compare_parameters: dict[str, float | str | bool] = Field(default_factory=dict)


class FilterGroup(BaseModel):
    id: str
    logic: Logic = "all"
    conditions: list[Condition] = Field(default_factory=list)


class ScanRequest(BaseModel):
    universe: str = "nifty50"
    timeframe: Timeframe = "1d"
    logic: Logic = "all"
    conditions: list[Condition] = Field(default_factory=list)
    groups: list[FilterGroup] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = "1d"
    initial_capital: float = Field(default=100000, gt=0)
    strategy_name: str = "Momentum baseline"
    parameters: dict[str, float] = Field(default_factory=dict)


class OrderPreviewRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"] = "BUY"
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    product: Literal["CNC", "MIS", "NRML"] = "MIS"


class LtpRequest(BaseModel):
    exchange: str = "NSE"
    symbol: str
    symbol_token: str


class CandleRequest(BaseModel):
    exchange: str = "NSE"
    symbol_token: str
    interval: str = "ONE_DAY"
    from_date: str
    to_date: str


SAMPLE_QUOTES = [
    {"symbol": "RELIANCE", "exchange": "NSE", "industry": "Refineries", "sector": "Energy", "marketcapname": "Large Cap", "open": 2894.0, "high": 2961.8, "low": 2882.3, "close": 2942.40, "ltp": 2942.40, "vwap": 2927.6, "change_pct": 1.84, "volume": 8420000, "rsi": 64.2, "score": 86, "fno_lot_size": 250},
    {"symbol": "ICICIBANK", "exchange": "NSE", "industry": "Private Sector Bank", "sector": "Banks", "marketcapname": "Large Cap", "open": 1309.4, "high": 1335.2, "low": 1305.1, "close": 1328.65, "ltp": 1328.65, "vwap": 1322.4, "change_pct": 1.25, "volume": 6110000, "rsi": 61.7, "score": 82, "fno_lot_size": 700},
    {"symbol": "BHARTIARTL", "exchange": "NSE", "industry": "Telecom Services", "sector": "Telecom", "marketcapname": "Large Cap", "open": 1826.0, "high": 1852.7, "low": 1818.9, "close": 1845.10, "ltp": 1845.10, "vwap": 1838.2, "change_pct": 0.94, "volume": 4340000, "rsi": 58.3, "score": 78, "fno_lot_size": 475},
    {"symbol": "TCS", "exchange": "NSE", "industry": "IT Services", "sector": "IT", "marketcapname": "Large Cap", "open": 4135.4, "high": 4152.0, "low": 4098.4, "close": 4120.75, "ltp": 4120.75, "vwap": 4124.8, "change_pct": -0.22, "volume": 2120000, "rsi": 49.6, "score": 57, "fno_lot_size": 175},
    {"symbol": "HDFCBANK", "exchange": "NSE", "industry": "Private Sector Bank", "sector": "Banks", "marketcapname": "Large Cap", "open": 1753.0, "high": 1772.8, "low": 1746.5, "close": 1764.20, "ltp": 1764.20, "vwap": 1761.3, "change_pct": 0.41, "volume": 5880000, "rsi": 55.1, "score": 71, "fno_lot_size": 550},
    {"symbol": "SUNPHARMA", "exchange": "NSE", "industry": "Pharmaceuticals", "sector": "Pharma", "marketcapname": "Large Cap", "open": 1701.2, "high": 1750.0, "low": 1695.8, "close": 1742.30, "ltp": 1742.30, "vwap": 1729.7, "change_pct": 2.32, "volume": 3020000, "rsi": 68.5, "score": 89, "fno_lot_size": 350},
    {"symbol": "INFY", "exchange": "NSE", "industry": "IT Services", "sector": "IT", "marketcapname": "Large Cap", "open": 1950.2, "high": 1958.4, "low": 1928.6, "close": 1936.55, "ltp": 1936.55, "vwap": 1941.5, "change_pct": -0.74, "volume": 3510000, "rsi": 44.9, "score": 46, "fno_lot_size": 400},
    {"symbol": "AXISBANK", "exchange": "NSE", "industry": "Private Sector Bank", "sector": "Banks", "marketcapname": "Large Cap", "open": 1202.8, "high": 1221.4, "low": 1198.9, "close": 1215.80, "ltp": 1215.80, "vwap": 1212.1, "change_pct": 0.86, "volume": 4790000, "rsi": 59.8, "score": 76, "fno_lot_size": 625},
]


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def rrg_points() -> list[dict]:
    names = [
        ("RELIANCE", "Energy", 102.6, 103.4),
        ("ICICIBANK", "Banks", 101.8, 102.2),
        ("SUNPHARMA", "Pharma", 103.5, 100.9),
        ("BHARTIARTL", "Telecom", 99.4, 101.3),
        ("TCS", "IT", 98.7, 99.1),
        ("INFY", "IT", 97.8, 98.4),
        ("AXISBANK", "Banks", 100.6, 99.2),
    ]
    points = []
    for index, (symbol, sector, ratio, momentum) in enumerate(names):
        trail = []
        for bar in range(20):
            trail.append(
                {
                    "x": round(ratio - math.sin((bar + index) / 4) * 2.2 - bar * 0.05, 2),
                    "y": round(momentum - math.cos((bar + index) / 5) * 2.0 - bar * 0.04, 2),
                }
            )
        if ratio >= 100 and momentum >= 100:
            quadrant = "leading"
        elif ratio >= 100 and momentum < 100:
            quadrant = "weakening"
        elif ratio < 100 and momentum < 100:
            quadrant = "lagging"
        else:
            quadrant = "improving"
        points.append(
            {
                "symbol": symbol,
                "sector": sector,
                "rsRatio": ratio,
                "rsMomentum": momentum,
                "quadrant": quadrant,
                "trail": trail,
            }
        )
    return points


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "allinonetrading-api", "mode": "demo-paper"}


@app.get("/api/v1/status")
def status() -> dict:
    return {
        "appMode": "demo",
        "paperTrading": env_bool("PAPER_TRADING", True),
        "liveTrading": env_bool("LIVE_TRADING", False),
        "broker": "Angel One SmartAPI (not connected)",
    }


@app.get("/api/v1/meta/universes")
def universes() -> dict:
    return {
        "universes": [
            {"key": "nifty50", "name": "NIFTY 50", "count": 50},
            {"key": "banknifty", "name": "BANKNIFTY", "count": 12},
            {"key": "midcap150", "name": "MIDCAP 150", "count": 150},
            {"key": "custom", "name": "Custom watchlist", "count": 0},
            {"key": "crypto", "name": "Crypto research", "count": 0},
        ]
    }


@app.get("/api/v1/screener/catalog")
def screener_catalog() -> dict:
    return catalog_response()


@app.post("/api/v1/screener/scan")
def run_scan(request: ScanRequest) -> dict:
    field_warnings = request_field_warnings(request)
    return {
        "mode": "demo",
        "universe": request.universe,
        "timeframe": request.timeframe,
        "logic": request.logic,
        "conditionsApplied": len(request.conditions) + sum(len(group.conditions) for group in request.groups),
        "groupsApplied": len(request.groups),
        "results": scan_rows(request, SAMPLE_QUOTES),
        "fieldWarnings": field_warnings,
        "warning": "The rule engine is active on deterministic demo/replay data. SmartAPI universe streaming is the next data-adapter step.",
    }


@app.get("/api/v1/rrg")
def rrg(universe: str = "nifty50", timeframe: Timeframe = "1d") -> dict:
    return {
        "mode": "demo",
        "universe": universe,
        "timeframe": timeframe,
        "trailBars": 20,
        "benchmark": "NIFTY 50",
        "points": rrg_points(),
        "warning": "RRG values are deterministic demo points until the data adapter is connected.",
    }


@app.post("/api/v1/backtest/preview")
def backtest_preview(request: BacktestRequest) -> dict:
    return {
        "mode": "demo",
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "strategy": request.strategy_name,
        "parameters": request.parameters,
        "metrics": {
            "net_return_pct": 18.42,
            "cagr_pct": 16.11,
            "max_drawdown_pct": -8.74,
            "sharpe": 1.31,
            "sortino": 1.78,
            "win_rate_pct": 58.3,
            "trades": 42,
            "profit_factor": 1.64,
        },
        "trades": [
            {"date": "2026-01-14", "side": "BUY", "price": 2380.0, "pnl": 4200.0},
            {"date": "2026-03-04", "side": "SELL", "price": 2524.0, "pnl": 6100.0},
        ],
        "warning": "This is a UI contract using demo output; no historical data has been loaded.",
    }


@app.post("/api/v1/trading/order-preview")
def order_preview(request: OrderPreviewRequest) -> dict:
    notional = request.quantity * request.price
    brokerage = min(20.0, notional * 0.0003)
    exchange_charge = notional * 0.0000325
    sebi_charge = notional * 0.000001
    stamp_duty = notional * 0.00003 if request.side == "BUY" else 0.0
    gst = (brokerage + exchange_charge + sebi_charge) * 0.18
    taxes_and_charges = brokerage + exchange_charge + sebi_charge + stamp_duty + gst
    multiplier = 0.2 if request.product == "MIS" else 1.0
    margin = notional * multiplier
    return {
        "mode": "paper",
        "symbol": request.symbol,
        "side": request.side,
        "quantity": request.quantity,
        "price": request.price,
        "product": request.product,
        "estimatedMargin": round(margin, 2),
        "brokerage": round(brokerage, 2),
        "taxesAndCharges": round(taxes_and_charges, 2),
        "totalCashImpact": round(margin + taxes_and_charges, 2),
        "breakeven": round(request.price + taxes_and_charges / request.quantity, 4),
        "warning": "Estimate only. Broker-provided margin and charge endpoints will replace this calculation.",
    }


@app.get("/api/v1/options/chain")
def option_chain(symbol: str = "NIFTY", expiry: str = "nearest") -> dict:
    center = 24500
    rows = []
    for offset in range(-4, 5):
        strike = center + offset * 100
        rows.append(
            {
                "strike": strike,
                "callLtp": round(max(20, 340 - abs(offset) * 48), 2),
                "callOi": max(10000, 84000 - abs(offset) * 7100),
                "callChangeOi": (-1 if offset > 1 else 1) * (2400 + abs(offset) * 300),
                "putLtp": round(max(18, 295 - abs(offset) * 42), 2),
                "putOi": max(9000, 76000 - abs(offset) * 6200),
                "putChangeOi": (1 if offset < 1 else -1) * (2100 + abs(offset) * 250),
                "iv": round(12.8 + abs(offset) * 0.8, 2),
            }
        )
    return {
        "mode": "demo",
        "symbol": symbol,
        "expiry": expiry,
        "underlying": center,
        "rows": rows,
        "warning": "Demo option chain. Live Greeks, IV and OI will come from a verified derivative-data adapter.",
    }


@app.get("/api/v1/arbitrage/scan")
def arbitrage_scan() -> dict:
    return {
        "mode": "paper",
        "opportunities": [],
        "checks": ["fees", "slippage", "latency", "withdrawal_cost", "funding_rate"],
        "warning": "Live crypto exchange connectors are not enabled.",
    }


@app.post("/api/v1/optimizer/preview")
def optimizer_preview() -> dict:
    return {
        "mode": "design",
        "searchMethods": ["grid", "random", "walk_forward", "bayesian"],
        "variables": [
            {"name": "fast_ema", "min": 5, "max": 50, "step": 5},
            {"name": "slow_ema", "min": 50, "max": 250, "step": 25},
            {"name": "stop_loss_pct", "min": 0.5, "max": 5.0, "step": 0.5},
        ],
        "status": "Optimizer contract ready; execution will be connected after historical data is loaded.",
    }


@app.post("/api/v1/research/analyze")
def research_analyze(request: ResearchRequest) -> dict:
    symbol = request.symbol.strip().upper()
    quote = next((item for item in SAMPLE_QUOTES if item["symbol"] == symbol), None)
    return build_research_report(request, quote).model_dump()


@app.get("/api/v1/broker/status")
def broker_status() -> dict:
    return AngelOneAdapter().configuration_status()


broker_adapter = AngelOneAdapter()


@app.post("/api/v1/broker/read-only-connect")
def broker_read_only_connect() -> dict:
    return broker_adapter.login()


@app.post("/api/v1/market/ltp")
def market_ltp(request: LtpRequest) -> dict:
    try:
        return {
            "mode": "connected",
            "data": broker_adapter.get_ltp(
                request.exchange,
                request.symbol,
                request.symbol_token,
            ),
        }
    except Exception as exc:
        return {
            "mode": "unavailable",
            "message": "Read-only quote request failed.",
            "error": type(exc).__name__,
        }


@app.post("/api/v1/market/candles")
def market_candles(request: CandleRequest) -> dict:
    try:
        return {
            "mode": "connected",
            "data": broker_adapter.get_candles(
                request.exchange,
                request.symbol_token,
                request.interval,
                request.from_date,
                request.to_date,
            ),
        }
    except Exception as exc:
        return {
            "mode": "unavailable",
            "message": "Read-only candle request failed.",
            "error": type(exc).__name__,
        }
