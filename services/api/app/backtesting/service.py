from __future__ import annotations

import itertools
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..brokers.angel_one import AngelOneAdapter
from .data import BacktestSource, load_history
from .engine import StrategyConfig, backtest, json_safe, performance_metrics, verdict
from .universe import NIFTY50_CURRENT


def _curve_points(curve: pd.DataFrame, initial_capital: float, limit: int = 500) -> list[dict[str, Any]]:
    if curve.empty:
        return []
    step = max(1, math.ceil(len(curve) / limit))
    sampled = curve.iloc[::step].copy()
    if sampled.index[-1] != curve.index[-1]:
        sampled = pd.concat([sampled, curve.iloc[[-1]]])
    first_close = float(curve["Close"].iloc[0])
    out = []
    for stamp, row in sampled.iterrows():
        out.append({
            "time": pd.Timestamp(stamp).isoformat(),
            "equity": float(row["Equity"]),
            "buyHold": float(initial_capital * float(row["Close"]) / first_close),
            "drawdownPct": float(row["DrawdownPct"]),
        })
    return out


def _trade_rows(trades: pd.DataFrame, limit: int = 2000) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    rows = trades.tail(limit).copy()
    for col in ("EntryTime", "ExitTime"):
        if col in rows:
            rows[col] = rows[col].map(lambda value: pd.Timestamp(value).isoformat())
    return json_safe(rows.to_dict(orient="records"))


def _coverage(bars: pd.DataFrame) -> dict[str, Any]:
    return {
        "bars": int(len(bars)),
        "from": pd.Timestamp(bars.index.min()).isoformat(),
        "to": pd.Timestamp(bars.index.max()).isoformat(),
        "approxYears": round((pd.Timestamp(bars.index.max()) - pd.Timestamp(bars.index.min())).days / 365.25, 2),
    }


def _base_result(bars: pd.DataFrame, cfg: StrategyConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], str, list[str]]:
    curve, trades = backtest(bars, cfg)
    metrics = performance_metrics(curve, trades, cfg.initial_capital)
    status, reasons = verdict(metrics)
    return curve, trades, metrics, status, reasons


def run_single_backtest(
    *,
    symbol: str,
    timeframe: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
    rsi_length: int,
    rsi_entry_threshold: float,
    vertex_length: int,
    vertex_entry_threshold: float,
    vertex_exit_threshold: float,
    match_export: bool,
    fill_mode: str,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    source: BacktestSource,
) -> dict[str, Any]:
    adapter = AngelOneAdapter() if source in {"auto", "angel_one"} else None
    data_result = load_history(symbol, start_date, end_date, timeframe, source, adapter)
    bars = data_result.bars
    cfg = StrategyConfig(
        rsi_length=rsi_length,
        rsi_entry_threshold=rsi_entry_threshold,
        vertex_length=vertex_length,
        vertex_entry_threshold=vertex_entry_threshold,
        vertex_exit_threshold=vertex_exit_threshold,
        match_export=match_export,
        fill_mode=fill_mode,  # type: ignore[arg-type]
        fee_bps_per_side=fee_bps_per_side,
        slippage_bps_per_side=slippage_bps_per_side,
        initial_capital=initial_capital,
    )
    curve, trades, metrics, status, reasons = _base_result(bars, cfg)

    split = int(len(bars) * 0.70)
    oos: list[dict[str, Any]] = []
    for label, piece in (("First 70%", bars.iloc[:split]), ("Last 30%", bars.iloc[split:])):
        if len(piece) <= max(20, vertex_length + rsi_length + 3):
            continue
        c, t = backtest(piece, cfg)
        m = performance_metrics(c, t, initial_capital)
        oos.append({
            "sample": label,
            "trades": m.get("Trades"),
            "returnPct": m.get("Total Return %"),
            "evPct": m.get("EV / Trade %"),
            "profitFactor": m.get("Profit Factor"),
            "maxDrawdownPct": m.get("Max Drawdown %"),
        })

    nearby: list[dict[str, Any]] = []
    rsi_values = sorted(set([max(1.0, rsi_entry_threshold - 2.5), rsi_entry_threshold, min(30.0, rsi_entry_threshold + 2.5)]))
    vertex_values = sorted(set([vertex_entry_threshold - 2.0, vertex_entry_threshold, vertex_entry_threshold + 2.0]))
    for rsi_value, vertex_value in itertools.product(rsi_values, vertex_values):
        rcfg = replace(cfg, rsi_entry_threshold=float(rsi_value), vertex_entry_threshold=float(vertex_value))
        c, t = backtest(bars, rcfg)
        m = performance_metrics(c, t, initial_capital)
        nearby.append({
            "rsiBelow": rsi_value,
            "vertexBelow": vertex_value,
            "trades": m.get("Trades"),
            "returnPct": m.get("Total Return %"),
            "evPct": m.get("EV / Trade %"),
            "profitFactor": m.get("Profit Factor"),
            "maxDrawdownPct": m.get("Max Drawdown %"),
        })

    execution: list[dict[str, Any]] = []
    for mode in ("next_open", "signal_close"):
        ecfg = replace(cfg, fill_mode=mode)  # type: ignore[arg-type]
        c, t = backtest(bars, ecfg)
        m = performance_metrics(c, t, initial_capital)
        execution.append({
            "fillMode": mode,
            "trades": m.get("Trades"),
            "returnPct": m.get("Total Return %"),
            "evPct": m.get("EV / Trade %"),
            "profitFactor": m.get("Profit Factor"),
            "maxDrawdownPct": m.get("Max Drawdown %"),
        })

    cost_stress: list[dict[str, Any]] = []
    for label, fee_mult, slip_mult in (("Base", 1.0, 1.0), ("1.5x costs", 1.5, 1.5), ("2x costs", 2.0, 2.0)):
        ccfg = replace(
            cfg,
            fee_bps_per_side=fee_bps_per_side * fee_mult,
            slippage_bps_per_side=slippage_bps_per_side * slip_mult,
        )
        c, t = backtest(bars, ccfg)
        m = performance_metrics(c, t, initial_capital)
        cost_stress.append({
            "scenario": label,
            "returnPct": m.get("Total Return %"),
            "evPct": m.get("EV / Trade %"),
            "profitFactor": m.get("Profit Factor"),
            "maxDrawdownPct": m.get("Max Drawdown %"),
            "totalFees": m.get("Total Fees"),
        })

    warnings = list(data_result.warnings)
    warnings.extend([
        "Backtests are research estimates, not forecasts. Confirm the unchanged rules with out-of-sample and paper trading before live capital.",
        "The default next-bar-open execution is intentionally more conservative than filling a close-confirmed signal at the same close.",
    ])
    return json_safe({
        "mode": "single",
        "strategy": "Vertex + RSI(3)",
        "symbol": symbol.strip().upper(),
        "timeframe": timeframe,
        "dataSource": data_result.source,
        "coverage": _coverage(bars),
        "config": {
            "rsiLength": rsi_length,
            "rsiEntryThreshold": rsi_entry_threshold,
            "vertexLength": vertex_length,
            "vertexEntryThreshold": vertex_entry_threshold,
            "vertexExitThreshold": vertex_exit_threshold,
            "matchExport": match_export,
            "fillMode": fill_mode,
            "feeBpsPerSide": fee_bps_per_side,
            "slippageBpsPerSide": slippage_bps_per_side,
            "initialCapital": initial_capital,
        },
        "verdict": status,
        "verdictReasons": reasons,
        "metrics": metrics,
        "equityCurve": _curve_points(curve, initial_capital),
        "trades": _trade_rows(trades),
        "robustness": {
            "outOfSample": oos,
            "nearbyParameters": nearby,
            "execution": execution,
            "costStress": cost_stress,
        },
        "warnings": warnings,
    })


def _portfolio_curve(curves: dict[str, pd.DataFrame], sleeve_capital: float) -> pd.DataFrame:
    if not curves:
        return pd.DataFrame()
    idx = pd.DatetimeIndex(sorted(set().union(*[set(curve.index) for curve in curves.values()])))
    equity_parts, benchmark_parts, position_parts = [], [], []
    for curve in curves.values():
        equity_parts.append(curve["Equity"].reindex(idx).ffill().fillna(sleeve_capital))
        first_close = float(curve["Close"].iloc[0])
        benchmark_parts.append((sleeve_capital * curve["Close"] / first_close).reindex(idx).ffill().fillna(sleeve_capital))
        position_parts.append(curve["Position"].reindex(idx).ffill().fillna(0.0))
    out = pd.DataFrame(index=idx)
    out["Equity"] = pd.concat(equity_parts, axis=1).sum(axis=1)
    out["Close"] = pd.concat(benchmark_parts, axis=1).sum(axis=1)
    out["Position"] = pd.concat(position_parts, axis=1).mean(axis=1)
    out["DrawdownPct"] = (out["Equity"] / out["Equity"].cummax() - 1.0) * 100.0
    return out


def run_nifty50_batch(
    *,
    timeframe: str,
    start_date: date,
    end_date: date,
    total_capital: float,
    rsi_length: int,
    rsi_entry_threshold: float,
    vertex_length: int,
    vertex_entry_threshold: float,
    vertex_exit_threshold: float,
    match_export: bool,
    fill_mode: str,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    source: BacktestSource,
) -> dict[str, Any]:
    if timeframe not in {"1d", "1wk"} and source != "angel_one":
        raise ValueError("10-year NIFTY 50 intraday batch tests require source='angel_one'. Yahoo cannot provide 10 years of intraday history.")
    sleeve_capital = total_capital / len(NIFTY50_CURRENT)
    cfg = StrategyConfig(
        rsi_length=rsi_length,
        rsi_entry_threshold=rsi_entry_threshold,
        vertex_length=vertex_length,
        vertex_entry_threshold=vertex_entry_threshold,
        vertex_exit_threshold=vertex_exit_threshold,
        match_export=match_export,
        fill_mode=fill_mode,  # type: ignore[arg-type]
        fee_bps_per_side=fee_bps_per_side,
        slippage_bps_per_side=slippage_bps_per_side,
        initial_capital=sleeve_capital,
    )
    rows: list[dict[str, Any]] = []
    trade_parts: list[pd.DataFrame] = []
    curves: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    source_labels: set[str] = set()

    def process(symbol: str) -> tuple[str, dict[str, Any], pd.DataFrame, pd.DataFrame, str]:
        result = load_history(symbol, start_date, end_date, timeframe, source)
        curve, trades = backtest(result.bars, cfg)
        metrics = performance_metrics(curve, trades, sleeve_capital)
        row = {"symbol": symbol, "company": NIFTY50_CURRENT[symbol], **_coverage(result.bars), **metrics}
        return symbol, row, curve, trades, result.source

    if source in {"auto", "yahoo"} and timeframe in {"1d", "1wk"}:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(process, symbol): symbol for symbol in NIFTY50_CURRENT}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    name, row, curve, trades, label = future.result()
                    rows.append(row)
                    curves[name] = curve
                    source_labels.add(label)
                    if not trades.empty:
                        part = trades.copy()
                        part.insert(0, "Symbol", name)
                        trade_parts.append(part)
                except Exception as exc:
                    errors.append(f"{symbol}: {exc}")
    else:
        adapter = AngelOneAdapter()
        if not adapter.configured:
            raise RuntimeError("Angel One credentials are required for the selected NIFTY 50 batch test.")
        for symbol in NIFTY50_CURRENT:
            try:
                result = load_history(symbol, start_date, end_date, timeframe, "angel_one", adapter)
                curve, trades = backtest(result.bars, cfg)
                metrics = performance_metrics(curve, trades, sleeve_capital)
                rows.append({"symbol": symbol, "company": NIFTY50_CURRENT[symbol], **_coverage(result.bars), **metrics})
                curves[symbol] = curve
                source_labels.add(result.source)
                if not trades.empty:
                    part = trades.copy()
                    part.insert(0, "Symbol", symbol)
                    trade_parts.append(part)
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")

    if not rows:
        raise RuntimeError("No NIFTY 50 symbols could be backtested.")
    stocks = pd.DataFrame(rows).sort_values("symbol")
    pooled_trades = pd.concat(trade_parts, ignore_index=True) if trade_parts else pd.DataFrame()
    portfolio = _portfolio_curve(curves, sleeve_capital)
    portfolio_metrics = performance_metrics(portfolio, pooled_trades, total_capital) if not portfolio.empty else {}
    status, reasons = verdict(portfolio_metrics)
    ev = pd.to_numeric(stocks["EV / Trade %"], errors="coerce")
    pf = pd.to_numeric(stocks["Profit Factor"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    returns = pd.to_numeric(stocks["Total Return %"], errors="coerce")
    diagnostics = {
        "requestedStocks": len(NIFTY50_CURRENT),
        "testedStocks": len(stocks),
        "failedStocks": len(errors),
        "totalTrades": int(pd.to_numeric(stocks["Trades"], errors="coerce").fillna(0).sum()),
        "stocksWithPositiveEV": int((ev > 0).sum()),
        "pctStocksPositiveEV": float((ev > 0).mean() * 100.0),
        "stocksProfitable": int((returns > 0).sum()),
        "pctStocksProfitable": float((returns > 0).mean() * 100.0),
        "medianStockEVPct": float(ev.median()),
        "medianStockProfitFactor": float(pf.median()),
        "medianStockReturnPct": float(returns.median()),
    }
    coverage_from = min(pd.Timestamp(curve.index.min()) for curve in curves.values())
    coverage_to = max(pd.Timestamp(curve.index.max()) for curve in curves.values())
    return json_safe({
        "mode": "nifty50_batch",
        "strategy": "Vertex + RSI(3)",
        "timeframe": timeframe,
        "dataSource": "; ".join(sorted(source_labels)),
        "coverage": {"from": coverage_from.isoformat(), "to": coverage_to.isoformat(), "testedStocks": len(stocks)},
        "verdict": status,
        "verdictReasons": reasons,
        "metrics": portfolio_metrics,
        "diagnostics": diagnostics,
        "stocks": stocks.to_dict(orient="records"),
        "equityCurve": _curve_points(portfolio, total_capital) if not portfolio.empty else [],
        "errors": errors,
        "warnings": [
            "This batch uses today's NIFTY 50 constituents across historical data, so survivorship bias is present.",
            "A portfolio result made from equal capital sleeves is a research diagnostic, not a claim that all positions could be entered simultaneously at identical liquidity.",
        ],
    })
