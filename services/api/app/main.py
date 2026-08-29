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
Operator = Literal[">", "<", ">=", "<=", "=", "crosses_above", "crosses_below"]


class Condition(BaseModel):
    id: str
    field: str
    operator: Operator
    value: float | str
    lookback: int = Field(default=0, ge=0)
    timeframe: Timeframe = "1d"


class ScanRequest(BaseModel):
    universe: str = "nifty50"
    timeframe: Timeframe = "1d"
    conditions: list[Condition] = Field(default_factory=list)
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
    {"symbol": "RELIANCE", "exchange": "NSE", "sector": "Energy", "ltp": 2942.40, "change_pct": 1.84, "volume": 8420000, "rsi": 64.2, "score": 86},
    {"symbol": "ICICIBANK", "exchange": "NSE", "sector": "Banks", "ltp": 1328.65, "change_pct": 1.25, "volume": 6110000, "rsi": 61.7, "score": 82},
    {"symbol": "BHARTIARTL", "exchange": "NSE", "sector": "Telecom", "ltp": 1845.10, "change_pct": 0.94, "volume": 4340000, "rsi": 58.3, "score": 78},
    {"symbol": "TCS", "exchange": "NSE", "sector": "IT", "ltp": 4120.75, "change_pct": -0.22, "volume": 2120000, "rsi": 49.6, "score": 57},
    {"symbol": "HDFCBANK", "exchange": "NSE", "sector": "Banks", "ltp": 1764.20, "change_pct": 0.41, "volume": 5880000, "rsi": 55.1, "score": 71},
    {"symbol": "SUNPHARMA", "exchange": "NSE", "sector": "Pharma", "ltp": 1742.30, "change_pct": 2.32, "volume": 3020000, "rsi": 68.5, "score": 89},
    {"symbol": "INFY", "exchange": "NSE", "sector": "IT", "ltp": 1936.55, "change_pct": -0.74, "volume": 3510000, "rsi": 44.9, "score": 46},
    {"symbol": "AXISBANK", "exchange": "NSE", "sector": "Banks", "ltp": 1215.80, "change_pct": 0.86, "volume": 4790000, "rsi": 59.8, "score": 76},
]


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def field_value(quote: dict, field: str) -> float | str | None:
    aliases = {
        "changePct": "change_pct",
        "change_percent": "change_pct",
        "lastPrice": "ltp",
        "price": "ltp",
    }
    return quote.get(aliases.get(field, field))


def matches_condition(quote: dict, condition: Condition) -> bool:
    actual = field_value(quote, condition.field)
    if actual is None:
        return False
    if condition.operator in {"crosses_above", "crosses_below"}:
        condition_operator = ">" if condition.operator == "crosses_above" else "<"
    else:
        condition_operator = condition.operator
    try:
        left = float(actual)
        right = float(condition.value)
        return {
            ">": left > right,
            "<": left < right,
            ">=": left >= right,
            "<=": left <= right,
            "=": abs(left - right) < 1e-9,
        }[condition_operator]
    except (TypeError, ValueError):
        return str(actual).lower() == str(condition.value).lower()


def scan_rows(request: ScanRequest) -> list[dict]:
    rows = []
    for quote in SAMPLE_QUOTES:
        if all(matches_condition(quote, condition) for condition in request.conditions):
            row = {
                "symbol": quote["symbol"],
                "exchange": quote["exchange"],
                "sector": quote["sector"],
                "ltp": quote["ltp"],
                "changePct": quote["change_pct"],
                "volume": quote["volume"],
                "signal": "Momentum" if quote["score"] >= 75 else "Watch",
                "score": quote["score"],
            }
            rows.append(row)
    return rows[: request.limit]


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


@app.post("/api/v1/screener/scan")
def run_scan(request: ScanRequest) -> dict:
    return {
        "mode": "demo",
        "universe": request.universe,
        "timeframe": request.timeframe,
        "conditionsApplied": len(request.conditions),
        "results": scan_rows(request),
        "warning": "Demo data only. SmartAPI market data is not connected yet.",
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
