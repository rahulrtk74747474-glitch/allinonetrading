from __future__ import annotations

import numpy as np
import pandas as pd

from app.backtesting import engine


def sample_bars() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=8, freq="D")
    return pd.DataFrame(
        {
            "Open": [100, 101, 105, 108, 110, 109, 111, 112],
            "High": [102, 103, 107, 110, 112, 111, 113, 114],
            "Low": [99, 100, 104, 107, 109, 108, 110, 111],
            "Close": [101, 102, 106, 109, 111, 110, 112, 113],
            "Volume": [1000] * 8,
        },
        index=index,
    )


def test_next_open_execution_uses_bar_after_signal(monkeypatch) -> None:
    bars = sample_bars()

    def fake_indicators(df: pd.DataFrame, cfg: engine.StrategyConfig) -> pd.DataFrame:
        out = engine.validate_ohlc(df)
        out["RSI"] = 50.0
        out["Vertex"] = 0.0
        out["EntrySignal"] = False
        out["ExitSignal"] = False
        out.loc[out.index[1], "EntrySignal"] = True
        out.loc[out.index[3], "ExitSignal"] = True
        return out

    monkeypatch.setattr(engine, "add_indicators", fake_indicators)
    cfg = engine.StrategyConfig(fee_bps_per_side=0, slippage_bps_per_side=0, initial_capital=100000)
    curve, trades = engine.backtest(bars, cfg)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["EntryTime"] == bars.index[2]
    assert trade["EntryFill"] == bars.iloc[2]["Open"]
    assert trade["ExitTime"] == bars.index[4]
    assert trade["ExitFill"] == bars.iloc[4]["Open"]
    assert curve.iloc[-1]["Equity"] > 0


def test_metrics_include_risk_and_expectancy_fields(monkeypatch) -> None:
    bars = sample_bars()

    def fake_indicators(df: pd.DataFrame, cfg: engine.StrategyConfig) -> pd.DataFrame:
        out = engine.validate_ohlc(df)
        out["RSI"] = 50.0
        out["Vertex"] = 0.0
        out["EntrySignal"] = False
        out["ExitSignal"] = False
        out.loc[out.index[1], "EntrySignal"] = True
        out.loc[out.index[3], "ExitSignal"] = True
        return out

    monkeypatch.setattr(engine, "add_indicators", fake_indicators)
    curve, trades = engine.backtest(bars, engine.StrategyConfig(fee_bps_per_side=0, slippage_bps_per_side=0))
    metrics = engine.performance_metrics(curve, trades, 100000)

    for key in ["EV / Trade %", "Profit Factor", "Max Drawdown %", "Sharpe (daily)", "Max Losing Streak", "Avg MFE %", "Avg MAE %"]:
        assert key in metrics
    assert metrics["Trades"] == 1
    assert np.isfinite(metrics["Total Return %"])
