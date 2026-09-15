from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

import httpx
import pandas as pd

from ..brokers.angel_one import AngelOneAdapter
from .engine import resample_ohlc, validate_ohlc
from .universe import yahoo_symbol

BacktestSource = Literal["auto", "yahoo", "angel_one"]
TIMEFRAMES = ("15m", "30m", "1h", "4h", "1d", "1wk")


@dataclass
class DataResult:
    bars: pd.DataFrame
    source: str
    warnings: list[str]


def _date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _yahoo_window(start: date, end: date, timeframe: str) -> tuple[date, list[str]]:
    warnings: list[str] = []
    requested = start
    if timeframe in {"15m", "30m"}:
        start = max(start, end - timedelta(days=59))
    elif timeframe in {"1h", "4h"}:
        start = max(start, end - timedelta(days=729))
    if start > requested:
        warnings.append(
            f"Yahoo limits {timeframe} intraday history; requested start {requested.isoformat()} was reduced to {start.isoformat()}. Use Angel One for longer intraday coverage."
        )
    return start, warnings


def download_yahoo(symbol: str, start: date | str, end: date | str, timeframe: str) -> DataResult:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    start_d, end_d = _date(start), _date(end)
    start_d, warnings = _yahoo_window(start_d, end_d, timeframe)
    interval = {"15m": "15m", "30m": "30m", "1h": "60m", "4h": "60m", "1d": "1d", "1wk": "1wk"}[timeframe]
    ticker = yahoo_symbol(symbol)
    period1 = int(datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.combine(end_d + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker, safe='^.-')}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": interval,
        "events": "div,splits",
        "includeAdjustedClose": "true",
        "includePrePost": "false",
    }
    try:
        with httpx.Client(timeout=35.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"Yahoo history request failed for {ticker}: {type(exc).__name__}") from exc
    chart = payload.get("chart") or {}
    if chart.get("error"):
        description = (chart.get("error") or {}).get("description") or "Yahoo rejected the history request."
        raise RuntimeError(str(description))
    results = chart.get("result") or []
    if not results:
        raise RuntimeError(f"No Yahoo history returned for {ticker}.")
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote_rows = (((result.get("indicators") or {}).get("quote") or [{}])[0])
    adjusted = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    if not timestamps:
        raise RuntimeError(f"No Yahoo bars returned for {ticker}.")
    rows = pd.DataFrame({
        "Datetime": pd.to_datetime(timestamps, unit="s", utc=True),
        "Open": quote_rows.get("open", []),
        "High": quote_rows.get("high", []),
        "Low": quote_rows.get("low", []),
        "Close": quote_rows.get("close", []),
        "Volume": quote_rows.get("volume", []),
    }).set_index("Datetime")
    if len(adjusted) == len(rows):
        adj = pd.to_numeric(pd.Series(adjusted, index=rows.index), errors="coerce")
        close = pd.to_numeric(rows["Close"], errors="coerce")
        factor = (adj / close).replace([float("inf"), float("-inf")], pd.NA).fillna(1.0)
        for col in ("Open", "High", "Low", "Close"):
            rows[col] = pd.to_numeric(rows[col], errors="coerce") * factor
    rows.index = rows.index.tz_convert("Asia/Kolkata").tz_localize(None)
    rows = validate_ohlc(rows)
    if timeframe == "4h":
        rows = resample_ohlc(rows, "4h")
    if rows.empty:
        raise RuntimeError(f"Yahoo returned no usable OHLC bars for {ticker}.")
    return DataResult(rows, f"Yahoo Finance ({ticker}, adjusted OHLC)", warnings)


def _resolve_token(adapter: AngelOneAdapter, symbol: str) -> str:
    client = adapter._client()
    response = client.searchScrip("NSE", f"{symbol.upper()}-EQ")
    rows = (response or {}).get("data") or []
    exact = f"{symbol.upper()}-EQ"
    for row in rows:
        if str(row.get("tradingsymbol", "")).upper() == exact:
            return str(row["symboltoken"])
    for row in rows:
        trading_symbol = str(row.get("tradingsymbol", "")).upper()
        if trading_symbol.startswith(symbol.upper()) and trading_symbol.endswith("-EQ"):
            return str(row["symboltoken"])
    raise RuntimeError(f"Could not resolve NSE token for {symbol}.")


def download_angel_one(
    symbol: str,
    start: date | str,
    end: date | str,
    timeframe: str,
    adapter: AngelOneAdapter | None = None,
) -> DataResult:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    adapter = adapter or AngelOneAdapter()
    if not adapter.configured:
        raise RuntimeError("Angel One credentials are not configured in the backend .env file.")
    token = _resolve_token(adapter, symbol)
    start_d, end_d = _date(start), _date(end)
    base_tf = "15m" if timeframe in {"15m", "30m", "1h", "4h"} else "1d"
    interval = "FIFTEEN_MINUTE" if base_tf == "15m" else "ONE_DAY"
    cursor = pd.Timestamp(start_d) + (pd.Timedelta(hours=9, minutes=15) if base_tf == "15m" else pd.Timedelta())
    finish = pd.Timestamp(end_d) + (pd.Timedelta(hours=15, minutes=30) if base_tf == "15m" else pd.Timedelta(hours=23, minutes=59))
    pieces: list[pd.DataFrame] = []
    while cursor <= finish:
        chunk_end = min(cursor + pd.Timedelta(days=199, hours=23, minutes=45), finish)
        response = adapter.get_candles(
            "NSE",
            token,
            interval,
            cursor.strftime("%Y-%m-%d %H:%M"),
            chunk_end.strftime("%Y-%m-%d %H:%M"),
        )
        values = (response or {}).get("data") or []
        if values:
            piece = pd.DataFrame(values, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
            piece["Datetime"] = pd.to_datetime(piece["Datetime"], errors="coerce")
            piece = piece.dropna(subset=["Datetime"]).set_index("Datetime")
            if getattr(piece.index, "tz", None) is not None:
                piece.index = piece.index.tz_convert("Asia/Kolkata").tz_localize(None)
            pieces.append(piece)
        cursor = chunk_end + (pd.Timedelta(minutes=15) if base_tf == "15m" else pd.Timedelta(days=1))
        time.sleep(0.36)
    if not pieces:
        raise RuntimeError(f"Angel One returned no history for {symbol}.")
    bars = validate_ohlc(pd.concat(pieces).sort_index())
    if timeframe != base_tf:
        bars = resample_ohlc(bars, timeframe)
    return DataResult(bars, f"Angel One SmartAPI ({symbol}-EQ)", [])


def load_history(
    symbol: str,
    start: date | str,
    end: date | str,
    timeframe: str,
    source: BacktestSource = "auto",
    adapter: AngelOneAdapter | None = None,
) -> DataResult:
    if source == "yahoo":
        return download_yahoo(symbol, start, end, timeframe)
    if source == "angel_one":
        return download_angel_one(symbol, start, end, timeframe, adapter)
    if timeframe in {"1d", "1wk"}:
        return download_yahoo(symbol, start, end, timeframe)
    candidate = adapter or AngelOneAdapter()
    if candidate.configured:
        return download_angel_one(symbol, start, end, timeframe, candidate)
    result = download_yahoo(symbol, start, end, timeframe)
    result.warnings.insert(0, "Angel One is not configured, so the app used Yahoo's shorter intraday window.")
    return result
