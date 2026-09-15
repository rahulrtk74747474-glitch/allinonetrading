from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StrategyConfig:
    rsi_length: int = 3
    rsi_entry_threshold: float = 10.0
    vertex_length: int = 14
    vertex_entry_threshold: float = -10.0
    vertex_exit_threshold: float = -10.0
    match_export: bool = True
    fill_mode: Literal["next_open", "signal_close"] = "next_open"
    fee_bps_per_side: float = 12.0
    slippage_bps_per_side: float = 3.0
    initial_capital: float = 100000.0


def validate_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("No OHLC data supplied.")
    out = df.copy()
    aliases = {str(c).strip().lower(): c for c in out.columns}
    rename: dict[object, str] = {}
    for name in ("open", "high", "low", "close"):
        if name not in aliases:
            raise ValueError(f"Missing required column: {name.title()}")
        rename[aliases[name]] = name.title()
    out = out.rename(columns=rename)
    for col in ("Open", "High", "Low", "Close"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if "Volume" in out.columns:
        out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out


def rma(series: pd.Series, length: int) -> pd.Series:
    if length < 1:
        raise ValueError("length must be >= 1")
    s = pd.to_numeric(series, errors="coerce").astype(float)
    values = s.to_numpy()
    out = np.full(len(values), np.nan, dtype=float)
    valid = np.flatnonzero(~np.isnan(values))
    if len(valid) < length:
        return pd.Series(out, index=s.index, name=s.name)
    seed_end = valid[length - 1]
    prev = float(np.mean(values[valid[:length]]))
    out[seed_end] = prev
    alpha = 1.0 / length
    for i in range(seed_end + 1, len(values)):
        x = values[i]
        if np.isnan(x):
            continue
        prev = alpha * x + (1.0 - alpha) * prev
        out[i] = prev
    return pd.Series(out, index=s.index, name=s.name)


def rsi_wilder(close: pd.Series, length: int = 3) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce").astype(float)
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = rma(gains, length)
    avg_loss = rma(losses, length)
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    rsi.name = f"RSI_{length}"
    return rsi


def vertex_control(df: pd.DataFrame, length: int = 14, use_previous_bar: bool = True) -> pd.Series:
    data = validate_ohlc(df)
    high = data["High"].to_numpy(float)
    low = data["Low"].to_numpy(float)
    close = data["Close"].to_numpy(float)
    result = np.full(len(data), np.nan, dtype=float)
    offset = 1 if use_previous_bar else 0
    for i in range(len(data)):
        running_high = np.nan
        running_low = np.nan
        up_sum = 0.0
        down_sum = 0.0
        used = 0
        for step in range(length):
            j = i - (offset + step)
            if j < 0 or np.isnan(close[j]):
                continue
            used += 1
            if np.isnan(running_high) or high[j] > running_high:
                running_high = high[j]
                up_sum += close[j]
            if np.isnan(running_low) or low[j] < running_low:
                running_low = low[j]
                down_sum += close[j]
        if used == 0:
            result[i] = 0.0
        elif up_sum and down_sum:
            result[i] = down_sum / up_sum - up_sum / down_sum
    return pd.Series(result, index=data.index, name="Vertex_Control")


def add_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    data = validate_ohlc(df)
    data["RSI"] = rsi_wilder(data["Close"], cfg.rsi_length)
    data["Vertex"] = vertex_control(data, cfg.vertex_length, cfg.match_export)
    data["EntrySignal"] = (data["RSI"] < cfg.rsi_entry_threshold) & (data["Vertex"] < cfg.vertex_entry_threshold)
    data["ExitSignal"] = data["Vertex"] > cfg.vertex_exit_threshold
    return data


def _trade_excursion(data: pd.DataFrame, entry_i: int, exit_i: int, entry_price: float) -> tuple[float, float]:
    window = data.iloc[entry_i : exit_i + 1]
    if window.empty or entry_price <= 0:
        return np.nan, np.nan
    return float(window["High"].max() / entry_price - 1.0), float(window["Low"].min() / entry_price - 1.0)


def backtest(df: pd.DataFrame, cfg: StrategyConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = add_indicators(df, cfg)
    n = len(data)
    if n < 3:
        raise ValueError("Not enough bars to backtest.")
    fee = cfg.fee_bps_per_side / 10000.0
    slip = cfg.slippage_bps_per_side / 10000.0
    cash = float(cfg.initial_capital)
    shares = 0.0
    in_position = False
    entry_i = entry_time = entry_raw = entry_fill = entry_capital = entry_fee = None
    pending_entry = pending_exit = False
    trades: list[dict] = []
    equity = np.zeros(n, dtype=float)
    position = np.zeros(n, dtype=int)

    def enter(i: int, raw_price: float) -> None:
        nonlocal cash, shares, in_position, entry_i, entry_time, entry_raw, entry_fill, entry_capital, entry_fee
        if in_position or raw_price <= 0 or np.isnan(raw_price):
            return
        entry_capital = cash
        entry_raw = float(raw_price)
        entry_fill = entry_raw * (1.0 + slip)
        shares = cash / (entry_fill * (1.0 + fee))
        entry_fee = shares * entry_fill * fee
        cash = 0.0
        in_position = True
        entry_i = i
        entry_time = data.index[i]

    def exit_(i: int, raw_price: float, forced: bool = False) -> None:
        nonlocal cash, shares, in_position, entry_i, entry_time, entry_raw, entry_fill, entry_capital, entry_fee
        if not in_position or raw_price <= 0 or np.isnan(raw_price):
            return
        exit_raw = float(raw_price)
        exit_fill = exit_raw * (1.0 - slip)
        gross_exit = shares * exit_fill
        exit_fee = gross_exit * fee
        cash = gross_exit - exit_fee
        capital = float(entry_capital)
        pnl = cash - capital
        net_return = cash / capital - 1.0
        gross_return = exit_raw / float(entry_raw) - 1.0
        mfe, mae = _trade_excursion(data, int(entry_i), i, float(entry_raw))
        trades.append({
            "EntryTime": entry_time,
            "ExitTime": data.index[i],
            "EntryPriceRaw": float(entry_raw),
            "EntryFill": float(entry_fill),
            "ExitPriceRaw": exit_raw,
            "ExitFill": exit_fill,
            "BarsHeld": int(i - int(entry_i) + 1),
            "GrossReturnPct": gross_return * 100.0,
            "NetReturnPct": net_return * 100.0,
            "PnL": pnl,
            "EntryCapital": capital,
            "Fees": float(entry_fee + exit_fee),
            "MFE_Pct": mfe * 100.0,
            "MAE_Pct": mae * 100.0,
            "ForcedExit": bool(forced),
        })
        shares = 0.0
        in_position = False
        entry_i = entry_time = entry_raw = entry_fill = entry_capital = entry_fee = None

    for i in range(n):
        if cfg.fill_mode == "next_open":
            if pending_exit and in_position:
                exit_(i, float(data["Open"].iloc[i]))
                pending_exit = False
            if pending_entry and not in_position:
                enter(i, float(data["Open"].iloc[i]))
                pending_entry = False
        if in_position:
            position[i] = 1
            equity[i] = shares * float(data["Close"].iloc[i])
        else:
            equity[i] = cash
        entry_sig = bool(data["EntrySignal"].iloc[i])
        exit_sig = bool(data["ExitSignal"].iloc[i])
        if cfg.fill_mode == "signal_close":
            if in_position and exit_sig:
                exit_(i, float(data["Close"].iloc[i]))
                equity[i] = cash
                position[i] = 0
            elif (not in_position) and entry_sig:
                enter(i, float(data["Close"].iloc[i]))
                position[i] = 1
                equity[i] = shares * float(data["Close"].iloc[i])
        else:
            if in_position and exit_sig and i < n - 1:
                pending_exit = True
            elif (not in_position) and entry_sig and i < n - 1:
                pending_entry = True
    if in_position:
        exit_(n - 1, float(data["Close"].iloc[-1]), forced=True)
        equity[-1] = cash
        position[-1] = 0
    data["Equity"] = equity
    data["Position"] = position
    data["DrawdownPct"] = (data["Equity"] / data["Equity"].cummax() - 1.0) * 100.0
    return data, pd.DataFrame(trades)


def resample_ohlc(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    data = validate_ohlc(df)
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("Data index must be a DatetimeIndex for resampling.")
    tf = timeframe.lower()
    rules = {"15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D", "1wk": "W-FRI"}
    if tf not in rules:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    agg: dict[str, str] = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in data.columns:
        agg["Volume"] = "sum"
    kwargs = {"origin": "start_day", "offset": "9h15min"} if tf in {"15m", "30m", "1h", "4h"} else {}
    return data.resample(rules[tf], **kwargs).agg(agg).dropna(subset=["Open", "High", "Low", "Close"])


def _safe_div(a: float, b: float | None) -> float:
    if b is None or pd.isna(b) or b == 0:
        return np.nan
    return a / b


def _streak(values: list[bool]) -> int:
    best = cur = 0
    for value in values:
        cur = cur + 1 if value else 0
        best = max(best, cur)
    return best


def _max_drawdown_duration(equity: pd.Series) -> int:
    underwater = equity < equity.cummax()
    return _streak(underwater.fillna(False).tolist())


def performance_metrics(curve: pd.DataFrame, trades: pd.DataFrame, initial_capital: float) -> dict[str, float | int]:
    equity = curve["Equity"].astype(float).dropna()
    if equity.empty:
        return {}
    start = float(initial_capital)
    end = float(equity.iloc[-1])
    total_return = end / start - 1.0
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 86400), 1 / 365.25) if isinstance(equity.index, pd.DatetimeIndex) else np.nan
    cagr = (end / start) ** (1.0 / years) - 1.0 if years and years > 0 and end > 0 else np.nan
    dd = equity / equity.cummax() - 1.0
    max_dd = float(dd.min()) if len(dd) else np.nan
    ulcer = float(np.sqrt(np.mean(np.square(np.minimum(dd.to_numpy(float), 0.0))))) if len(dd) else np.nan
    daily_eq = equity.resample("1D").last().dropna() if isinstance(equity.index, pd.DatetimeIndex) else equity
    daily_ret = daily_eq.pct_change().dropna()
    sharpe = sortino = var95 = cvar95 = np.nan
    if len(daily_ret) >= 2 and daily_ret.std(ddof=1) > 0:
        sharpe = float(np.sqrt(252) * daily_ret.mean() / daily_ret.std(ddof=1))
        downside = daily_ret[daily_ret < 0]
        if len(downside) >= 2 and downside.std(ddof=1) > 0:
            sortino = float(np.sqrt(252) * daily_ret.mean() / downside.std(ddof=1))
        var95 = float(np.quantile(daily_ret, 0.05))
        tail = daily_ret[daily_ret <= var95]
        cvar95 = float(tail.mean()) if len(tail) else np.nan
    n = len(trades)
    if n:
        returns = trades["NetReturnPct"].astype(float) / 100.0
        pnl = trades["PnL"].astype(float)
        winners = returns[returns > 0]
        losers = returns[returns < 0]
        win_rate = float((returns > 0).mean())
        avg_win = float(winners.mean()) if len(winners) else np.nan
        avg_loss = float(losers.mean()) if len(losers) else np.nan
        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = float(-pnl[pnl < 0].sum())
        profit_factor = _safe_div(gross_profit, gross_loss)
        expectancy = float(returns.mean())
        expectancy_amount = float(pnl.mean())
        payoff = _safe_div(avg_win, abs(avg_loss) if not pd.isna(avg_loss) else np.nan)
        breakeven = _safe_div(abs(avg_loss) if not pd.isna(avg_loss) else np.nan, (avg_win if not pd.isna(avg_win) else 0) + (abs(avg_loss) if not pd.isna(avg_loss) else 0))
        kelly = win_rate - _safe_div(1.0 - win_rate, payoff) if payoff and not pd.isna(payoff) else np.nan
        sqn = float(math.sqrt(n) * returns.mean() / returns.std(ddof=1)) if n >= 2 and returns.std(ddof=1) > 0 else np.nan
        max_loss_streak = _streak((returns <= 0).tolist())
        max_win_streak = _streak((returns > 0).tolist())
        avg_bars = float(trades["BarsHeld"].mean())
        fees = float(trades["Fees"].sum())
        avg_mfe = float(trades["MFE_Pct"].mean()) / 100.0
        avg_mae = float(trades["MAE_Pct"].mean()) / 100.0
        best_trade = float(returns.max())
        worst_trade = float(returns.min())
        median_trade = float(returns.median())
    else:
        win_rate = avg_win = avg_loss = profit_factor = expectancy = expectancy_amount = payoff = breakeven = kelly = sqn = np.nan
        max_loss_streak = max_win_streak = 0
        avg_bars = fees = 0.0
        avg_mfe = avg_mae = best_trade = worst_trade = median_trade = np.nan
    benchmark = float(curve["Close"].iloc[-1] / curve["Close"].iloc[0] - 1.0) if len(curve) > 1 else np.nan
    exposure = float(curve["Position"].mean()) if "Position" in curve else np.nan
    calmar = _safe_div(cagr, abs(max_dd) if not pd.isna(max_dd) else np.nan)
    recovery = _safe_div(end - start, abs(start * max_dd) if not pd.isna(max_dd) else np.nan)
    return {
        "Ending Equity": end, "Net Profit": end - start, "Total Return %": total_return * 100,
        "CAGR %": cagr * 100 if not pd.isna(cagr) else np.nan, "Buy & Hold %": benchmark * 100,
        "Trades": n, "Win Rate %": win_rate * 100 if not pd.isna(win_rate) else np.nan,
        "Loss Rate %": (1 - win_rate) * 100 if not pd.isna(win_rate) else np.nan,
        "Profit Factor": profit_factor, "EV / Trade %": expectancy * 100 if not pd.isna(expectancy) else np.nan,
        "EV / Trade Amount": expectancy_amount, "Avg Win %": avg_win * 100 if not pd.isna(avg_win) else np.nan,
        "Avg Loss %": avg_loss * 100 if not pd.isna(avg_loss) else np.nan, "Payoff Ratio": payoff,
        "Breakeven Win Rate %": breakeven * 100 if not pd.isna(breakeven) else np.nan,
        "Best Trade %": best_trade * 100 if not pd.isna(best_trade) else np.nan,
        "Worst Trade %": worst_trade * 100 if not pd.isna(worst_trade) else np.nan,
        "Median Trade %": median_trade * 100 if not pd.isna(median_trade) else np.nan,
        "Max Drawdown %": max_dd * 100 if not pd.isna(max_dd) else np.nan,
        "Max DD Duration (bars)": _max_drawdown_duration(equity),
        "Ulcer Index %": ulcer * 100 if not pd.isna(ulcer) else np.nan,
        "Sharpe (daily)": sharpe, "Sortino (daily)": sortino, "Calmar": calmar, "Recovery Factor": recovery,
        "SQN": sqn, "Max Losing Streak": max_loss_streak, "Max Winning Streak": max_win_streak,
        "Exposure %": exposure * 100 if not pd.isna(exposure) else np.nan, "Avg Bars Held": avg_bars,
        "Avg MFE %": avg_mfe * 100 if not pd.isna(avg_mfe) else np.nan,
        "Avg MAE %": avg_mae * 100 if not pd.isna(avg_mae) else np.nan,
        "Total Fees": fees, "Approx Kelly %": kelly * 100 if not pd.isna(kelly) else np.nan,
        "Daily VaR 95%": var95 * 100 if not pd.isna(var95) else np.nan,
        "Daily CVaR 95%": cvar95 * 100 if not pd.isna(cvar95) else np.nan,
    }


def verdict(metrics: dict[str, float | int]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    trades = int(metrics.get("Trades", 0) or 0)
    ev = metrics.get("EV / Trade %", np.nan)
    pf = metrics.get("Profit Factor", np.nan)
    dd = metrics.get("Max Drawdown %", np.nan)
    sharpe = metrics.get("Sharpe (daily)", np.nan)
    if trades < 30:
        reasons.append(f"Only {trades} trades: sample is too small for a reliable conclusion.")
    if pd.isna(ev) or float(ev) <= 0:
        reasons.append("Net expectancy is not positive after modeled costs.")
    if pd.isna(pf) or float(pf) < 1.2:
        reasons.append("Profit factor is below the 1.2 research hurdle.")
    if not pd.isna(dd) and float(dd) < -25:
        reasons.append("Maximum drawdown is worse than -25%.")
    if not pd.isna(sharpe) and float(sharpe) < 0.5:
        reasons.append("Daily Sharpe is below 0.5.")
    if reasons:
        return "NOT READY FOR LIVE MONEY", reasons
    return "PROMISING — STILL REQUIRES OUT-OF-SAMPLE + PAPER TRADING", ["Core statistical hurdles passed in this sample, but live execution and regime risk remain untested."]


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value
