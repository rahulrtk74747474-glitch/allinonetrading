from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from .service import run_nifty50_batch, run_single_backtest

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])
BacktestTimeframe = Literal["15m", "30m", "1h", "4h", "1d", "1wk"]
BacktestSource = Literal["auto", "yahoo", "angel_one"]
FillMode = Literal["next_open", "signal_close"]
BacktestMode = Literal["single", "nifty50_batch"]


class QuantBacktestRequest(BaseModel):
    mode: BacktestMode = "single"
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=50, pattern=r"^[A-Za-z0-9.^_&-]+$")
    timeframe: BacktestTimeframe = "1d"
    start_date: date = date(2016, 9, 15)
    end_date: date = date(2026, 9, 15)
    initial_capital: float = Field(default=100000.0, ge=1000.0, le=1_000_000_000.0)
    rsi_length: int = Field(default=3, ge=2, le=100)
    rsi_entry_threshold: float = Field(default=10.0, ge=0.0, le=100.0)
    vertex_length: int = Field(default=14, ge=2, le=200)
    vertex_entry_threshold: float = Field(default=-10.0, ge=-1000.0, le=1000.0)
    vertex_exit_threshold: float = Field(default=-10.0, ge=-1000.0, le=1000.0)
    match_export: bool = True
    fill_mode: FillMode = "next_open"
    fee_bps_per_side: float = Field(default=12.0, ge=0.0, le=500.0)
    slippage_bps_per_side: float = Field(default=3.0, ge=0.0, le=500.0)
    source: BacktestSource = "auto"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


@router.get("/config")
def backtest_config() -> dict:
    return {
        "strategy": "Vertex + RSI(3)",
        "timeframes": ["15m", "30m", "1h", "4h", "1d", "1wk"],
        "defaults": {
            "entry": "RSI(3) < 10 AND Vertex < -10 on a completed bar",
            "exit": "Vertex > -10 on a completed bar",
            "vertexLength": 14,
            "matchExport": True,
            "fillMode": "next_open",
            "feeBpsPerSide": 12.0,
            "slippageBpsPerSide": 3.0,
        },
        "modes": ["single", "nifty50_batch"],
    }


@router.post("/run")
def run_backtest(request: QuantBacktestRequest) -> dict:
    common = dict(
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        rsi_length=request.rsi_length,
        rsi_entry_threshold=request.rsi_entry_threshold,
        vertex_length=request.vertex_length,
        vertex_entry_threshold=request.vertex_entry_threshold,
        vertex_exit_threshold=request.vertex_exit_threshold,
        match_export=request.match_export,
        fill_mode=request.fill_mode,
        fee_bps_per_side=request.fee_bps_per_side,
        slippage_bps_per_side=request.slippage_bps_per_side,
        source=request.source,
    )
    try:
        if request.mode == "nifty50_batch":
            return run_nifty50_batch(total_capital=request.initial_capital, **common)
        return run_single_backtest(symbol=request.symbol, initial_capital=request.initial_capital, **common)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
