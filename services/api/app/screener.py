from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import fmean, pstdev
from typing import Any

from .fundamental_catalog import CATEGORY_META, FUNDAMENTAL_FIELDS, FUNDAMENTAL_FIELD_IDS


def field(
    field_id: str,
    label: str,
    category: str,
    *,
    kind: str = "field",
    value_type: str = "number",
    description: str = "",
    availability: str = "ready",
    parameters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": field_id,
        "label": label,
        "category": category,
        "kind": kind,
        "valueType": value_type,
        "description": description,
        "availability": availability,
        "parameters": parameters or [],
    }


SOURCE_PARAMETER = {
    "name": "source",
    "label": "Input field",
    "type": "field",
    "default": "close",
}
PERIOD_PARAMETER = {
    "name": "period",
    "label": "Period",
    "type": "number",
    "default": 20,
    "min": 1,
    "max": 500,
}
GROUP_PARAMETER = {
    "name": "groupBy",
    "label": "Group by",
    "type": "select",
    "default": "sector",
    "options": ["sector", "industry", "marketcapname"],
}


SCREENER_FIELDS: list[dict[str, Any]] = [
    # Measures shown at the top of the Chartink picker.
    field("sub_filter", "Sub-Filter / Group", "measures", kind="group", value_type="group", description="Create an ALL/ANY nested condition group."),
    field("number", "Number", "measures", kind="measure", description="Compare the selected field with a numeric constant."),

    # Stock attributes and candle-derived values.
    field("symbol", "Symbol", "stock_attributes", value_type="string"),
    field("industry", "Industry", "stock_attributes", value_type="string", availability="metadata_required"),
    field("sector", "Sector", "stock_attributes", value_type="string", availability="metadata_required"),
    field("marketcapname", "Marketcap name", "stock_attributes", value_type="string", availability="metadata_required"),
    field("open", "Open", "stock_attributes"),
    field("high", "High", "stock_attributes"),
    field("low", "Low", "stock_attributes"),
    field("close", "Close", "stock_attributes"),
    field("volume", "Volume", "stock_attributes"),
    field("change_pct", "% Change", "stock_attributes"),
    field("vwap", "VWAP", "stock_attributes"),
    field("ha_open", "HA-Open (Heikin-Ashi)", "stock_attributes"),
    field("ha_high", "HA-High (Heikin-Ashi)", "stock_attributes"),
    field("ha_low", "HA-Low (Heikin-Ashi)", "stock_attributes"),
    field("ha_close", "HA-Close (Heikin-Ashi)", "stock_attributes"),
    field("fno_lot_size", "FnO lot size", "stock_attributes", availability="metadata_required"),
    field("hl2", "HL2", "stock_attributes", description="(High + Low) / 2"),
    field("hlc3", "HLC3", "stock_attributes", description="(High + Low + Close) / 3"),
    field("ohlc4", "OHLC4", "stock_attributes", description="(Open + High + Low + Close) / 4"),

    # Tick-classified trades. These are visible and usable with replay/demo data,
    # but live scans need a dedicated tick feed rather than an LTP snapshot.
    field("buyer_initiated_trades", "Buyer initiated trades", "trade_book", availability="tick_feed_required"),
    field("buyer_initiated_trades_quantity", "Buyer initiated trades quantity", "trade_book", availability="tick_feed_required"),
    field("buyer_initiated_trades_avg_quantity", "Buyer initiated trades average quantity", "trade_book", availability="tick_feed_required"),
    field("seller_initiated_trades", "Seller initiated trades", "trade_book", availability="tick_feed_required"),
    field("seller_initiated_trades_quantity", "Seller initiated trades quantity", "trade_book", availability="tick_feed_required"),
    field("seller_initiated_trades_avg_quantity", "Seller initiated trades average quantity", "trade_book", availability="tick_feed_required"),
    field("buyer_seller_trades_ratio", "Buyer vs Seller initiated trades ratio", "trade_book", availability="tick_feed_required"),
    field("buyer_seller_trade_quantity_ratio", "Buyer vs Seller initiated trades quantity ratio", "trade_book", availability="tick_feed_required"),
    field("buyer_initiated_vwap", "Buyer initiated trades VWAP", "trade_book", availability="tick_feed_required"),
    field("seller_initiated_vwap", "Seller initiated trades VWAP", "trade_book", availability="tick_feed_required"),

    # Order-depth fields. SmartAPI FULL mode can cover current depth, while
    # cancellation history still requires locally accumulated depth events.
    field("orders", "Orders", "order_book", availability="depth_feed_required"),
    field("orders_quantity", "Orders Quantity", "order_book", availability="depth_feed_required"),
    field("buy_orders", "Buy Orders", "order_book", availability="depth_feed_required"),
    field("buy_orders_quantity", "Buy Orders Quantity", "order_book", availability="depth_feed_required"),
    field("sell_orders", "Sell Orders", "order_book", availability="depth_feed_required"),
    field("sell_orders_quantity", "Sell Orders Quantity", "order_book", availability="depth_feed_required"),
    field("buy_sell_orders_ratio", "Buy vs Sell orders ratio", "order_book", availability="depth_feed_required"),
    field("buy_sell_order_quantity_ratio", "Buy vs Sell orders quantity ratio", "order_book", availability="depth_feed_required"),
    field("cancelled_buy_orders", "Cancelled Buy Orders", "order_book", availability="depth_history_required"),
    field("cancelled_buy_orders_quantity", "Cancelled Buy Orders Quantity", "order_book", availability="depth_history_required"),
    field("cancelled_sell_orders", "Cancelled Sell Orders", "order_book", availability="depth_history_required"),
    field("cancelled_sell_orders_quantity", "Cancelled Sell Orders Quantity", "order_book", availability="depth_history_required"),
    field("total_cancelled_orders", "Total Cancelled orders", "order_book", availability="depth_history_required"),
    field("total_cancelled_orders_quantity", "Total Cancelled orders quantity", "order_book", availability="depth_history_required"),
    field("cancelled_orders_ratio", "Cancelled orders ratio", "order_book", availability="depth_history_required"),
    field("cancelled_order_quantity_ratio", "Cancelled orders quantity ratio", "order_book", availability="depth_history_required"),
    field("buy_orders_vwap", "Buy Orders VWAP", "order_book", availability="depth_feed_required"),
    field("sell_orders_vwap", "Sell Orders VWAP", "order_book", availability="depth_feed_required"),
    field("orders_vwap", "Orders VWAP", "order_book", availability="depth_feed_required"),

    # Group functions aggregate the selected source within sector, industry or
    # market-cap group in the current scan universe.
    field("group_count", "GroupCount (total rows in a group)", "group_functions", kind="function", parameters=[GROUP_PARAMETER]),
    field("group_low", "GroupLow (min of the group)", "group_functions", kind="function", parameters=[SOURCE_PARAMETER, GROUP_PARAMETER]),
    field("group_high", "GroupHigh (max of the group)", "group_functions", kind="function", parameters=[SOURCE_PARAMETER, GROUP_PARAMETER]),
    field("group_avg", "GroupAvg (avg of the group)", "group_functions", kind="function", parameters=[SOURCE_PARAMETER, GROUP_PARAMETER]),
    field("group_sum", "GroupSum (sum of the group)", "group_functions", kind="function", parameters=[SOURCE_PARAMETER, GROUP_PARAMETER]),

    # Math and rolling functions visible in the screenshots.
    field("bracket", "Bracket (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("min", "Min (duration, value)", "math_functions", kind="function", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("max", "Max (duration, value)", "math_functions", kind="function", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("greatest", "Greatest (fields..)", "math_functions", kind="function", parameters=[{"name": "fields", "label": "Fields", "type": "text", "default": "open,high,low,close"}]),
    field("least", "Least (fields..)", "math_functions", kind="function", parameters=[{"name": "fields", "label": "Fields", "type": "text", "default": "open,high,low,close"}]),
    field("count", "Count (duration, filter)", "math_functions", kind="function", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER, {"name": "threshold", "label": "Threshold", "type": "number", "default": 0}, {"name": "predicate", "label": "Predicate", "type": "select", "default": ">", "options": [">", "<", ">=", "<=", "="]}]),
    field("countstreak", "Countstreak (duration, filter)", "math_functions", kind="function", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER, {"name": "threshold", "label": "Threshold", "type": "number", "default": 0}, {"name": "predicate", "label": "Predicate", "type": "select", "default": ">", "options": [">", "<", ">=", "<=", "="]}]),
    field("abs", "Abs (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("ceil", "Ceil (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("floor", "Floor (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("round", "Round (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER, {"name": "decimals", "label": "Decimals", "type": "number", "default": 2, "min": 0, "max": 8}]),
    field("square", "Square (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("sqrt", "Square root (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("log", "Log (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),
    field("log10", "Log10 (value)", "math_functions", kind="function", parameters=[SOURCE_PARAMETER]),

    # Standard floor pivots from the previous bar.
    field("pivot_point", "Pivot point", "pivots"),
    field("pivot_r1", "Pivot point R1", "pivots"),
    field("pivot_r2", "Pivot point R2", "pivots"),
    field("pivot_r3", "Pivot point R3", "pivots"),
    field("pivot_s1", "Pivot point S1", "pivots"),
    field("pivot_s2", "Pivot point S2", "pivots"),
    field("pivot_s3", "Pivot point S3", "pivots"),

    # Common indicators, including every indicator visible in image 10.
    field("rsi", "RSI", "indicators", kind="indicator", parameters=[{"name": "period", "label": "Period", "type": "number", "default": 14, "min": 2, "max": 200}]),
    field("sma", "SMA (Simple)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("ema", "EMA (Exponential)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("wma", "WMA (Weighted)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("tma", "TMA (Triangular)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("rma", "RMA (Rolling Moving Average)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("tema", "TEMA (Triple EMA)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("hma", "HMA (Hull moving average)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("vwma", "VWMA (Volume-weighted avg)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("std", "Std (Standard Deviation)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("sum", "Sum (total for the given period)", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("parabolic_sar", "Parabolic SAR", "indicators", kind="indicator", parameters=[{"name": "step", "label": "Step", "type": "number", "default": 0.02}, {"name": "maximum", "label": "Maximum", "type": "number", "default": 0.2}]),
    field("bollinger_upper", "Upper Bollinger band", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER, {"name": "stddev", "label": "Std deviations", "type": "number", "default": 2}]),
    field("bollinger_middle", "Middle Bollinger band", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER]),
    field("bollinger_lower", "Lower Bollinger band", "indicators", kind="indicator", parameters=[PERIOD_PARAMETER, SOURCE_PARAMETER, {"name": "stddev", "label": "Std deviations", "type": "number", "default": 2}]),
    field("score", "Momentum score", "indicators"),

    # Provider-backed statement, ratio and ownership fields. These are never
    # synthesized from prices: a missing imported value resolves to None.
    *FUNDAMENTAL_FIELDS,
]


CATEGORY_LABELS = {
    "measures": "Measures",
    "stock_attributes": "Stock attributes",
    "trade_book": "Trade Book fields",
    "order_book": "Order Book fields",
    "group_functions": "Group Functions",
    "math_functions": "Math Functions",
    "pivots": "Pivots",
    "indicators": "Indicators",
    **{category_id: str(metadata["label"]) for category_id, metadata in CATEGORY_META.items()},
}

FIELD_INDEX = {item["id"]: item for item in SCREENER_FIELDS}


def catalog_response() -> dict[str, Any]:
    categories = []
    for category_id, label in CATEGORY_LABELS.items():
        categories.append(
            {
                "id": category_id,
                "label": label,
                "items": [item for item in SCREENER_FIELDS if item["category"] == category_id],
            }
        )
    return {
        "version": "2026.09.2",
        "categories": categories,
        "operators": {
            "number": [">", "<", ">=", "<=", "=", "!=", "crosses_above", "crosses_below"],
            "string": ["=", "!=", "contains", "not_contains", "starts_with", "ends_with"],
        },
        "operatorLabels": {
            "=": "Equals",
            "!=": "Not equals",
            ">": "Greater than",
            ">=": "Greater than or equal to",
            "<": "Less than",
            "<=": "Less than or equal to",
            "crosses_above": "Crossed above",
            "crosses_below": "Crossed below",
            "contains": "Contains",
            "not_contains": "Does not contain",
            "starts_with": "Starts with",
            "ends_with": "Ends with",
        },
        "availability": {
            "ready": "Calculated from OHLCV or the current scan universe.",
            "metadata_required": "Needs instrument/company metadata for live universes.",
            "tick_feed_required": "Needs classified tick-by-tick trades for live scans.",
            "depth_feed_required": "Needs current market-depth snapshots for live scans.",
            "depth_history_required": "Needs locally accumulated depth events for live scans.",
            "fundamentals_required": "Needs a verified financial-results provider or imported dataset.",
            "shareholding_required": "Needs a verified shareholding-pattern provider or imported dataset.",
            "cashflow_required": "Needs a verified cash-flow provider or imported dataset.",
        },
    }


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _safe_ratio(left: float, right: float) -> float:
    return left / right if right else 0.0


def _period(parameters: dict[str, Any], default: int = 20) -> int:
    return max(1, min(500, int(_number(parameters.get("period")) or default)))


def _generated_close_history(quote: dict[str, Any], bars: int = 520) -> list[float]:
    explicit = quote.get("history")
    if isinstance(explicit, list) and explicit:
        return [float(value) for value in explicit if _number(value) is not None]
    close = float(quote.get("close", quote.get("ltp", 0.0)))
    score = float(quote.get("score", 50.0))
    symbol_seed = sum(ord(character) for character in str(quote.get("symbol", ""))) % 29
    series: list[float] = []
    for index in range(bars):
        distance = bars - index - 1
        drift = (score - 50.0) * 0.00008 * distance
        wave = math.sin((index + symbol_seed) / 7.0) * 0.012
        smaller_wave = math.cos((index + symbol_seed) / 19.0) * 0.006
        series.append(round(close * max(0.2, 1.0 - drift + wave + smaller_wave), 4))
    series[-1] = close
    return series


def _series(quote: dict[str, Any], source: str) -> list[float]:
    closes = _generated_close_history(quote)
    if source in FUNDAMENTAL_FIELD_IDS:
        fundamentals = quote.get("fundamentals", {})
        value = _number(fundamentals.get(source)) if isinstance(fundamentals, dict) else None
        return [value for _ in closes] if value is not None else []
    if source in {"close", "ltp"}:
        return closes
    seed = (sum(ord(character) for character in str(quote.get("symbol", ""))) % 11) + 2
    if source == "open":
        values = [round(value * (1 + math.sin((index + seed) / 5) * 0.003), 4) for index, value in enumerate(closes)]
        values[-1] = float(quote.get("open", values[-1]))
        return values
    if source == "high":
        values = [round(value * (1.004 + abs(math.sin((index + seed) / 6)) * 0.009), 4) for index, value in enumerate(closes)]
        values[-1] = float(quote.get("high", values[-1]))
        return values
    if source == "low":
        values = [round(value * (0.996 - abs(math.cos((index + seed) / 6)) * 0.009), 4) for index, value in enumerate(closes)]
        values[-1] = float(quote.get("low", values[-1]))
        return values
    if source == "volume":
        current = float(quote.get("volume", 1.0))
        values = [max(1.0, current * (0.72 + abs(math.sin((index + seed) / 4)) * 0.5)) for index in range(len(closes))]
        values[-1] = current
        return values
    if source == "change_pct":
        values = [0.0]
        values.extend(_safe_ratio(current - previous, previous) * 100 for previous, current in zip(closes, closes[1:]))
        values[-1] = float(quote.get("change_pct", values[-1]))
        return values
    if source == "vwap":
        explicit_vwap = quote.get("vwap_history")
        if isinstance(explicit_vwap, list) and explicit_vwap:
            return [float(value) for value in explicit_vwap if _number(value) is not None]
        highs = _series(quote, "high")
        lows = _series(quote, "low")
        values = [(high + low + close) / 3 for high, low, close in zip(highs, lows, closes)]
        values[-1] = float(quote.get("vwap", values[-1]))
        return values
    if source in {"hl2", "hlc3", "ohlc4"}:
        opens = _series(quote, "open")
        highs = _series(quote, "high")
        lows = _series(quote, "low")
        if source == "hl2":
            return [(high + low) / 2 for high, low in zip(highs, lows)]
        if source == "hlc3":
            return [(high + low + close) / 3 for high, low, close in zip(highs, lows, closes)]
        return [
            (open_price + high + low + close) / 4
            for open_price, high, low, close in zip(opens, highs, lows, closes)
        ]
    if source in {"ha_open", "ha_high", "ha_low", "ha_close"}:
        opens = _series(quote, "open")
        highs = _series(quote, "high")
        lows = _series(quote, "low")
        ha_opens: list[float] = []
        ha_highs: list[float] = []
        ha_lows: list[float] = []
        ha_closes: list[float] = []
        for open_price, high, low, close in zip(opens, highs, lows, closes):
            ha_close = (open_price + high + low + close) / 4
            ha_open = (open_price + close) / 2 if not ha_opens else (ha_opens[-1] + ha_closes[-1]) / 2
            ha_opens.append(ha_open)
            ha_closes.append(ha_close)
            ha_highs.append(max(high, ha_open, ha_close))
            ha_lows.append(min(low, ha_open, ha_close))
        return {
            "ha_open": ha_opens,
            "ha_high": ha_highs,
            "ha_low": ha_lows,
            "ha_close": ha_closes,
        }[source]
    if source.startswith("pivot_"):
        highs = _series(quote, "high")
        lows = _series(quote, "low")
        result: list[float] = []
        for index in range(len(closes)):
            previous = max(0, index - 1)
            high = highs[previous]
            low = lows[previous]
            close = closes[previous]
            pivot = (high + low + close) / 3
            result.append({
                "pivot_point": pivot,
                "pivot_r1": 2 * pivot - low,
                "pivot_r2": pivot + (high - low),
                "pivot_r3": high + 2 * (pivot - low),
                "pivot_s1": 2 * pivot - high,
                "pivot_s2": pivot - (high - low),
                "pivot_s3": low - 2 * (high - pivot),
            }.get(source, pivot))
        return result
    definition = FIELD_INDEX.get(source)
    if definition and definition["category"] in {"trade_book", "order_book"}:
        value = _demo_depth_value(quote, source)
        return [value for _ in closes]
    direct = _number(quote.get(source))
    if direct is not None:
        return [direct for _ in closes]
    return closes


def _sma(values: list[float], period: int) -> float:
    window = values[-period:]
    return fmean(window) if window else 0.0


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def _wma(values: list[float], period: int) -> float:
    window = values[-period:]
    weights = list(range(1, len(window) + 1))
    return _safe_ratio(sum(value * weight for value, weight in zip(window, weights)), sum(weights))


def _rma(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    result = values[0]
    alpha = 1.0 / period
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def _rsi(values: list[float], period: int) -> float:
    if len(values) < 2:
        return 50.0
    changes = [current - previous for previous, current in zip(values, values[1:])]
    window = changes[-period:]
    gains = [max(change, 0.0) for change in window]
    losses = [max(-change, 0.0) for change in window]
    average_gain = fmean(gains) if gains else 0.0
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0 if average_gain else 50.0
    return 100.0 - (100.0 / (1.0 + average_gain / average_loss))


def _predicate(value: float, operator: str, threshold: float) -> bool:
    return {
        ">": value > threshold,
        "<": value < threshold,
        ">=": value >= threshold,
        "<=": value <= threshold,
        "=": math.isclose(value, threshold, rel_tol=1e-9, abs_tol=1e-9),
    }.get(operator, False)


def _parabolic_sar(quote: dict[str, Any], step: float, maximum: float) -> float:
    highs = _series(quote, "high")[-80:]
    lows = _series(quote, "low")[-80:]
    if len(highs) < 2:
        return lows[-1] if lows else 0.0
    rising = True
    sar = lows[0]
    extreme = highs[0]
    acceleration = step
    for index in range(1, len(highs)):
        candidate = sar + acceleration * (extreme - sar)
        if rising:
            if lows[index] < candidate:
                rising = False
                sar = extreme
                extreme = lows[index]
                acceleration = step
            else:
                previous_lows = lows[max(0, index - 2):index]
                sar = min(candidate, *previous_lows)
                if highs[index] > extreme:
                    extreme = highs[index]
                    acceleration = min(maximum, acceleration + step)
        else:
            if highs[index] > candidate:
                rising = True
                sar = extreme
                extreme = highs[index]
                acceleration = step
            else:
                previous_highs = highs[max(0, index - 2):index]
                sar = max(candidate, *previous_highs)
                if lows[index] < extreme:
                    extreme = lows[index]
                    acceleration = min(maximum, acceleration + step)
    return sar


def _demo_depth_value(quote: dict[str, Any], field_id: str) -> float:
    volume = float(quote.get("volume", 0.0))
    close = float(quote.get("close", quote.get("ltp", 0.0)))
    score = float(quote.get("score", 50.0))
    buyer_share = min(0.78, max(0.22, 0.46 + (score - 50) / 220))
    seller_share = 1 - buyer_share
    buyer_quantity = volume * buyer_share
    seller_quantity = volume * seller_share
    buyer_trades = max(1.0, buyer_quantity / max(12.0, 95.0 - score))
    seller_trades = max(1.0, seller_quantity / max(12.0, 35.0 + score))
    buy_orders = max(1.0, buyer_trades * 0.42)
    sell_orders = max(1.0, seller_trades * 0.42)
    cancelled_buy = buy_orders * 0.08
    cancelled_sell = sell_orders * 0.08
    cancelled_buy_quantity = buyer_quantity * 0.045
    cancelled_sell_quantity = seller_quantity * 0.045
    values = {
        "buyer_initiated_trades": buyer_trades,
        "buyer_initiated_trades_quantity": buyer_quantity,
        "buyer_initiated_trades_avg_quantity": _safe_ratio(buyer_quantity, buyer_trades),
        "seller_initiated_trades": seller_trades,
        "seller_initiated_trades_quantity": seller_quantity,
        "seller_initiated_trades_avg_quantity": _safe_ratio(seller_quantity, seller_trades),
        "buyer_seller_trades_ratio": _safe_ratio(buyer_trades, seller_trades),
        "buyer_seller_trade_quantity_ratio": _safe_ratio(buyer_quantity, seller_quantity),
        "buyer_initiated_vwap": close * 1.0008,
        "seller_initiated_vwap": close * 0.9992,
        "orders": buy_orders + sell_orders,
        "orders_quantity": buyer_quantity + seller_quantity,
        "buy_orders": buy_orders,
        "buy_orders_quantity": buyer_quantity,
        "sell_orders": sell_orders,
        "sell_orders_quantity": seller_quantity,
        "buy_sell_orders_ratio": _safe_ratio(buy_orders, sell_orders),
        "buy_sell_order_quantity_ratio": _safe_ratio(buyer_quantity, seller_quantity),
        "cancelled_buy_orders": cancelled_buy,
        "cancelled_buy_orders_quantity": cancelled_buy_quantity,
        "cancelled_sell_orders": cancelled_sell,
        "cancelled_sell_orders_quantity": cancelled_sell_quantity,
        "total_cancelled_orders": cancelled_buy + cancelled_sell,
        "total_cancelled_orders_quantity": cancelled_buy_quantity + cancelled_sell_quantity,
        "cancelled_orders_ratio": _safe_ratio(cancelled_buy, cancelled_sell),
        "cancelled_order_quantity_ratio": _safe_ratio(cancelled_buy_quantity, cancelled_sell_quantity),
        "buy_orders_vwap": close * 0.9995,
        "sell_orders_vwap": close * 1.0005,
        "orders_vwap": close,
    }
    return values.get(field_id, 0.0)


def _base_value(quote: dict[str, Any], field_id: str, lookback: int = 0) -> float | str | None:
    aliases = {
        "changePct": "change_pct",
        "change_percent": "change_pct",
        "lastPrice": "close",
        "ltp": "close",
        "price": "close",
    }
    field_id = aliases.get(field_id, field_id)
    definition = FIELD_INDEX.get(field_id)
    if field_id in FUNDAMENTAL_FIELD_IDS:
        fundamentals = quote.get("fundamentals", {})
        if not isinstance(fundamentals, dict):
            return None
        # The initial provider contract stores the latest verified snapshot.
        # Bars-ago/crossing support will require dated snapshot history.
        if lookback:
            return None
        return _number(fundamentals.get(field_id))
    if field_id in {"symbol", "industry", "sector", "marketcapname"}:
        return str(quote.get(field_id, ""))
    if lookback and definition and definition["kind"] == "field" and definition["valueType"] == "number":
        values = _series(quote, field_id)
        index = max(0, len(values) - 1 - lookback)
        return values[index]
    computed = bool(
        definition
        and (
            definition["kind"] in {"function", "indicator"}
            or definition["category"] == "pivots"
        )
        and field_id != "score"
    )
    if not computed:
        direct = _number(quote.get(field_id))
        if direct is not None:
            return direct
    if field_id in {"hl2", "hlc3", "ohlc4", "ha_open", "ha_high", "ha_low", "ha_close"}:
        return _series(quote, field_id)[-1]
    open_price = float(quote.get("open", quote.get("close", quote.get("ltp", 0.0))))
    high = float(quote.get("high", quote.get("close", quote.get("ltp", 0.0))))
    low = float(quote.get("low", quote.get("close", quote.get("ltp", 0.0))))
    close = float(quote.get("close", quote.get("ltp", 0.0)))
    previous_close = _series(quote, "close")[-2]
    previous_open = _series(quote, "open")[-2]
    ha_close = (open_price + high + low + close) / 4
    ha_open = (previous_open + previous_close) / 2
    derived = {
        "close": close,
        "change_pct": _safe_ratio(close - previous_close, previous_close) * 100,
        "hl2": (high + low) / 2,
        "hlc3": (high + low + close) / 3,
        "ohlc4": (open_price + high + low + close) / 4,
        "ha_open": ha_open,
        "ha_close": ha_close,
        "ha_high": max(high, ha_open, ha_close),
        "ha_low": min(low, ha_open, ha_close),
    }
    if field_id in derived:
        return derived[field_id]
    if field_id in FIELD_INDEX and FIELD_INDEX[field_id]["category"] in {"trade_book", "order_book"}:
        return _demo_depth_value(quote, field_id)
    return None


def resolve_value(
    quote: dict[str, Any],
    field_id: str,
    parameters: dict[str, Any] | None,
    universe: list[dict[str, Any]],
    lookback: int = 0,
) -> float | str | None:
    parameters = parameters or {}
    base = _base_value(quote, field_id, lookback)
    if base is not None:
        return base

    source = str(parameters.get("source", "close"))
    values = _series(quote, source)
    if lookback:
        values = values[: max(1, len(values) - lookback)]
    period = _period(parameters)

    if field_id.startswith("group_"):
        group_by = str(parameters.get("groupBy", "sector"))
        group_value = quote.get(group_by)
        peers = [item for item in universe if item.get(group_by) == group_value]
        if field_id == "group_count":
            return float(len(peers))
        peer_values = [
            _number(resolve_value(item, source, {}, universe))
            for item in peers
        ]
        numbers = [value for value in peer_values if value is not None]
        if not numbers:
            return None
        return {
            "group_low": min(numbers),
            "group_high": max(numbers),
            "group_avg": fmean(numbers),
            "group_sum": sum(numbers),
        }.get(field_id)

    if field_id == "bracket":
        return resolve_value(quote, source, {}, universe, lookback)
    if field_id == "min":
        return min(values[-period:]) if values else None
    if field_id == "max":
        return max(values[-period:]) if values else None
    if field_id in {"greatest", "least"}:
        names = [name.strip() for name in str(parameters.get("fields", "open,high,low,close")).split(",") if name.strip()]
        candidates = [_number(resolve_value(quote, name, {}, universe, lookback)) for name in names]
        numbers = [value for value in candidates if value is not None]
        if not numbers:
            return None
        return max(numbers) if field_id == "greatest" else min(numbers)
    if field_id in {"count", "countstreak"}:
        if not values:
            return None
        threshold = float(_number(parameters.get("threshold")) or 0.0)
        predicate = str(parameters.get("predicate", ">"))
        window = values[-period:]
        flags = [_predicate(value, predicate, threshold) for value in window]
        if field_id == "count":
            return float(sum(flags))
        streak = 0
        for flag in reversed(flags):
            if not flag:
                break
            streak += 1
        return float(streak)

    current = _number(resolve_value(quote, source, {}, universe, lookback))
    if current is None:
        return None
    if field_id == "abs":
        return abs(current)
    if field_id == "ceil":
        return float(math.ceil(current))
    if field_id == "floor":
        return float(math.floor(current))
    if field_id == "round":
        return round(current, max(0, min(8, int(_number(parameters.get("decimals")) or 2))))
    if field_id == "square":
        return current * current
    if field_id == "sqrt":
        return math.sqrt(current) if current >= 0 else None
    if field_id == "log":
        return math.log(current) if current > 0 else None
    if field_id == "log10":
        return math.log10(current) if current > 0 else None

    previous_high = _series(quote, "high")[-2]
    previous_low = _series(quote, "low")[-2]
    previous_close = _series(quote, "close")[-2]
    pivot = (previous_high + previous_low + previous_close) / 3
    pivot_values = {
        "pivot_point": pivot,
        "pivot_r1": 2 * pivot - previous_low,
        "pivot_r2": pivot + (previous_high - previous_low),
        "pivot_r3": previous_high + 2 * (pivot - previous_low),
        "pivot_s1": 2 * pivot - previous_high,
        "pivot_s2": pivot - (previous_high - previous_low),
        "pivot_s3": previous_low - 2 * (previous_high - pivot),
    }
    if field_id in pivot_values:
        return pivot_values[field_id]

    if field_id == "rsi":
        return _rsi(values, period)
    if field_id == "sma":
        return _sma(values, period)
    if field_id == "ema":
        return _ema_series(values, period)[-1]
    if field_id == "wma":
        return _wma(values, period)
    if field_id == "tma":
        first_period = max(1, math.ceil((period + 1) / 2))
        smoothed = [_sma(values[: index + 1], first_period) for index in range(len(values))]
        return _sma(smoothed, max(1, math.floor((period + 1) / 2)))
    if field_id == "rma":
        return _rma(values, period)
    if field_id == "tema":
        ema_one = _ema_series(values, period)
        ema_two = _ema_series(ema_one, period)
        ema_three = _ema_series(ema_two, period)
        return 3 * ema_one[-1] - 3 * ema_two[-1] + ema_three[-1]
    if field_id == "hma":
        half = max(1, period // 2)
        root = max(1, int(math.sqrt(period)))
        synthetic: list[float] = []
        for index in range(1, len(values) + 1):
            prefix = values[:index]
            synthetic.append(2 * _wma(prefix, half) - _wma(prefix, period))
        return _wma(synthetic, root)
    if field_id == "vwma":
        volume_values = _series(quote, "volume")[-period:]
        source_values = values[-period:]
        return _safe_ratio(sum(value * volume for value, volume in zip(source_values, volume_values)), sum(volume_values))
    if field_id == "std":
        window = values[-period:]
        return pstdev(window) if len(window) > 1 else 0.0
    if field_id == "sum":
        return sum(values[-period:])
    if field_id == "parabolic_sar":
        step = float(_number(parameters.get("step")) or 0.02)
        maximum = float(_number(parameters.get("maximum")) or 0.2)
        return _parabolic_sar(quote, step, maximum)
    if field_id.startswith("bollinger_"):
        middle = _sma(values, period)
        window = values[-period:]
        deviation = (pstdev(window) if len(window) > 1 else 0.0) * float(_number(parameters.get("stddev")) or 2.0)
        if field_id == "bollinger_upper":
            return middle + deviation
        if field_id == "bollinger_lower":
            return middle - deviation
        return middle
    return None


def _compare(left: float | str | None, operator: str, right: float | str | None) -> bool:
    if left is None or right is None:
        return False
    left_number = _number(left)
    right_number = _number(right)
    if left_number is not None and right_number is not None:
        return {
            ">": left_number > right_number,
            "<": left_number < right_number,
            ">=": left_number >= right_number,
            "<=": left_number <= right_number,
            "=": math.isclose(left_number, right_number, rel_tol=1e-9, abs_tol=1e-9),
            "!=": not math.isclose(left_number, right_number, rel_tol=1e-9, abs_tol=1e-9),
        }.get(operator, False)
    left_text = str(left).casefold()
    right_text = str(right).casefold()
    return {
        "=": left_text == right_text,
        "!=": left_text != right_text,
        "contains": right_text in left_text,
        "not_contains": right_text not in left_text,
        "starts_with": left_text.startswith(right_text),
        "ends_with": left_text.endswith(right_text),
    }.get(operator, False)


def condition_matches(quote: dict[str, Any], condition: Any, universe: list[dict[str, Any]]) -> bool:
    parameters = getattr(condition, "parameters", {}) or {}
    lookback = int(getattr(condition, "lookback", 0) or 0)
    left = resolve_value(quote, condition.field, parameters, universe, lookback)
    compare_field = getattr(condition, "compare_field", None)
    if compare_field:
        right = resolve_value(
            quote,
            compare_field,
            getattr(condition, "compare_parameters", {}) or {},
            universe,
            lookback,
        )
    else:
        right = condition.value
    if condition.operator in {"crosses_above", "crosses_below"}:
        current_operator = ">" if condition.operator == "crosses_above" else "<"
        previous_operator = "<=" if condition.operator == "crosses_above" else ">="
        previous_left = resolve_value(quote, condition.field, parameters, universe, lookback + 1)
        previous_right = (
            resolve_value(
                quote,
                compare_field,
                getattr(condition, "compare_parameters", {}) or {},
                universe,
                lookback + 1,
            )
            if compare_field
            else right
        )
        return _compare(left, current_operator, right) and _compare(previous_left, previous_operator, previous_right)
    return _compare(left, condition.operator, right)


def _combine(values: Iterable[bool], logic: str) -> bool:
    items = list(values)
    if not items:
        return True
    return any(items) if logic == "any" else all(items)


def scan_rows(request: Any, quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for quote in quotes:
        top_results = [condition_matches(quote, condition, quotes) for condition in request.conditions]
        group_results = [
            _combine(
                (condition_matches(quote, condition, quotes) for condition in group.conditions),
                group.logic,
            )
            for group in getattr(request, "groups", [])
        ]
        if _combine([*top_results, *group_results], getattr(request, "logic", "all")):
            selected_metrics = {
                condition.field: resolve_value(
                    quote,
                    condition.field,
                    getattr(condition, "parameters", {}) or {},
                    quotes,
                    int(getattr(condition, "lookback", 0) or 0),
                )
                for condition in request.conditions
            }
            rows.append(
                {
                    "symbol": quote["symbol"],
                    "exchange": quote.get("exchange", "NSE"),
                    "sector": quote.get("sector", "Unknown"),
                    "ltp": float(quote.get("close", quote.get("ltp", 0.0))),
                    "changePct": float(quote.get("change_pct", 0.0)),
                    "volume": int(quote.get("volume", 0)),
                    "signal": "Momentum" if quote.get("score", 0) >= 75 else "Watch",
                    "score": int(quote.get("score", 0)),
                    "metrics": selected_metrics,
                }
            )
    return rows[: request.limit]


def request_field_warnings(
    request: Any,
    quotes: list[dict[str, Any]] | None = None,
) -> list[str]:
    field_ids: set[str] = set()
    all_conditions = list(request.conditions)
    for group in getattr(request, "groups", []):
        all_conditions.extend(group.conditions)

    def add_parameter_fields(field_id: str | None, parameters: dict[str, Any]) -> None:
        definition = FIELD_INDEX.get(field_id or "")
        if definition is None:
            return
        for parameter in definition["parameters"]:
            if parameter.get("type") != "field":
                continue
            referenced = parameters.get(parameter["name"], parameter.get("default"))
            if isinstance(referenced, str):
                field_ids.add(referenced)
        if field_id in {"greatest", "least"}:
            names = str(parameters.get("fields", "open,high,low,close")).split(",")
            field_ids.update(name.strip() for name in names if name.strip())

    for condition in all_conditions:
        field_ids.add(condition.field)
        add_parameter_fields(condition.field, getattr(condition, "parameters", {}) or {})
        compare_field = getattr(condition, "compare_field", None)
        if compare_field:
            field_ids.add(compare_field)
            add_parameter_fields(compare_field, getattr(condition, "compare_parameters", {}) or {})

    warnings: list[str] = []
    by_availability: dict[str, list[dict[str, Any]]] = {}
    for field_id in sorted(field_ids):
        definition = FIELD_INDEX.get(field_id)
        if definition is None:
            warnings.append(f"Unknown screener field: {field_id}.")
            continue
        availability = definition["availability"]
        if availability != "ready":
            by_availability.setdefault(availability, []).append(definition)
    messages = {
        "metadata_required": "Live metadata mapping is required",
        "tick_feed_required": "Classified tick data is required for live trade-book fields",
        "depth_feed_required": "SmartAPI FULL depth snapshots are required for live order-book fields",
        "depth_history_required": "Locally accumulated depth history is required for cancellation fields",
        "fundamentals_required": "A verified financial-results import/provider is required",
        "shareholding_required": "A verified shareholding-pattern import/provider is required",
        "cashflow_required": "A verified cash-flow import/provider is required",
    }
    for availability, definitions in by_availability.items():
        labels = [definition["label"] for definition in definitions]
        if availability in {"fundamentals_required", "shareholding_required", "cashflow_required"}:
            required_ids = {definition["id"] for definition in definitions}
            covered_rows = 0
            if quotes is not None:
                covered_rows = sum(
                    required_ids.issubset(
                        set(quote.get("fundamentals", {}))
                        if isinstance(quote.get("fundamentals"), dict)
                        else set()
                    )
                    for quote in quotes
                )
            if covered_rows:
                warnings.append(
                    f"Imported {availability.replace('_required', '')} data covers all selected fields for "
                    f"{covered_rows}/{len(quotes or [])} scanned symbols. Rows with missing values do not match."
                )
            else:
                warnings.append(
                    f"{messages[availability]}: {', '.join(labels)}. "
                    "Rows with missing values do not match; no fundamental values are synthesized."
                )
        else:
            warnings.append(f"{messages.get(availability, availability)}: {', '.join(labels)}. Demo/replay evaluation remains available.")
    crossed_snapshot_fields = [
        condition.field
        for condition in all_conditions
        if condition.operator in {"crosses_above", "crosses_below"}
        and (
            condition.field in FUNDAMENTAL_FIELD_IDS
            or any(
                value in FUNDAMENTAL_FIELD_IDS
                for value in (getattr(condition, "parameters", {}) or {}).values()
                if isinstance(value, str)
            )
        )
    ]
    if crossed_snapshot_fields:
        warnings.append(
            "Crossed above/below on fundamentals needs dated snapshot history; the current import contract stores the latest snapshot only."
        )
    return warnings
