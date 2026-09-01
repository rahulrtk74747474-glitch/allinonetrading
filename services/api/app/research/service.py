from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping

from .models import (
    ResearchEvidence,
    ResearchFinding,
    ResearchMode,
    ResearchReport,
    ResearchRequest,
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_research_report(
    request: ResearchRequest,
    quote: Mapping[str, object] | None,
    mode: ResearchMode = "demo",
) -> ResearchReport:
    symbol = request.symbol.strip().upper()
    as_of = utc_timestamp()
    quote_available = quote is not None
    source = "demo-snapshot" if quote_available else "unavailable-snapshot"

    ltp = _number(quote.get("ltp") if quote else None)
    change_pct = _number(quote.get("change_pct") if quote else None)
    rsi = _number(quote.get("rsi") if quote else None, 50.0)
    score = _number(quote.get("score") if quote else None, 50.0)
    volume = _number(quote.get("volume") if quote else None)

    quote_id = "quote-snapshot"
    quote_status = "demo" if quote_available else "not_loaded"
    direction = "positive" if change_pct >= 0 else "negative"
    technical_confidence = 0.68 if quote_available else 0.2

    if quote_available and score >= 80 and 50 <= rsi <= 70 and change_pct > 0:
        decision = "paper_candidate"
        summary = (
            f"{symbol} has a positive demo momentum snapshot: score {score:.0f}, "
            f"RSI {rsi:.1f}, and {change_pct:+.2f}% daily change."
        )
        decision_confidence = 0.68
    elif quote_available and (rsi >= 75 or change_pct < -2):
        decision = "no_trade"
        summary = (
            f"{symbol} is flagged for caution in the demo snapshot: RSI {rsi:.1f}, "
            f"{change_pct:+.2f}% daily change, and score {score:.0f}."
        )
        decision_confidence = 0.6
    else:
        decision = "watch"
        summary = (
            f"{symbol} remains a watch candidate in the demo snapshot; "
            "more verified data is required before paper testing."
        )
        decision_confidence = 0.45 if quote_available else 0.2

    evidence = [
        ResearchEvidence(
            id=quote_id,
            role="technical",
            source=source,
            as_of=as_of,
            status=quote_status,
            summary=(
                f"LTP {ltp:.2f}, daily change {change_pct:+.2f}%, RSI {rsi:.1f}, "
                f"volume {volume:.0f}, momentum score {score:.0f}."
            ),
            values={
                "ltp": round(ltp, 4),
                "change_pct": round(change_pct, 4),
                "rsi": round(rsi, 4),
                "volume": round(volume, 2),
                "score": round(score, 4),
            },
        )
    ]

    findings = [
        ResearchFinding(
            role="technical",
            title="Technical snapshot",
            conclusion=(
                f"The demo snapshot is {direction}; its deterministic score is {score:.0f}/100 "
                f"with RSI {rsi:.1f}."
            ),
            confidence=technical_confidence,
            evidence_ids=[quote_id],
        ),
        ResearchFinding(
            role="fundamental",
            title="Fundamental review",
            conclusion=(
                "Fundamental data is not loaded. Do not infer valuation, earnings quality, "
                "financial health or corporate actions from this packet."
            ),
            confidence=0.0,
            evidence_ids=[],
        ),
        ResearchFinding(
            role="news",
            title="News review",
            conclusion=(
                "News and RSS data are not loaded. Event risk and sentiment are unknown."
            ),
            confidence=0.0,
            evidence_ids=[],
        ),
        ResearchFinding(
            role="risk",
            title="Risk review",
            conclusion=(
                "Treat this as a paper-research hypothesis only; verify liquidity, gaps, "
                "charges, slippage and portfolio exposure before testing."
            ),
            confidence=0.62 if quote_available else 0.2,
            evidence_ids=[quote_id],
        ),
    ]

    if request.include_fundamentals:
        evidence.append(
            ResearchEvidence(
                id="fundamental-snapshot",
                role="fundamental",
                source="not-configured",
                as_of=as_of,
                status="not_loaded",
                summary="A verified fundamentals provider is not configured.",
            )
        )
    if request.include_news:
        evidence.append(
            ResearchEvidence(
                id="news-snapshot",
                role="news",
                source="not-configured",
                as_of=as_of,
                status="not_loaded",
                summary="A verified news/RSS provider is not configured.",
            )
        )

    report_key = f"{symbol}|{request.timeframe}|{as_of}"
    report_id = "research-" + sha256(report_key.encode("utf-8")).hexdigest()[:12]
    warnings = [
        "Demo output only; this is not investment advice or a live trading signal.",
        "Research agents have no order authority; manual approval is required for paper actions.",
        "Historical candles, fundamentals, news, corporate actions and live charges are not verified.",
    ]
    if not quote_available:
        warnings.append("The requested symbol is not present in the current demo universe.")

    return ResearchReport(
        report_id=report_id,
        symbol=symbol,
        timeframe=request.timeframe,
        universe=request.universe,
        mode=mode,
        data_quality="demo",
        as_of=as_of,
        decision=decision,
        confidence=decision_confidence,
        summary=summary,
        findings=findings,
        evidence=evidence,
        risks=[
            "No look-ahead-safe historical window has been loaded for this report.",
            "Slippage, taxes, liquidity, gaps and corporate actions are not modeled here.",
            "News and fundamentals are unavailable unless their evidence status is available.",
        ],
        next_actions=[
            "Load a verified market-data snapshot and corporate-action adjustment.",
            "Run the same hypothesis through fees, slippage and out-of-sample backtesting.",
            "Create a paper order only after manual review of the evidence and risk budget.",
        ],
        agent_trace=[
            "snapshot:" + source,
            "technical:deterministic-v1",
            "fundamental:" + ("requested-but-not-loaded" if request.include_fundamentals else "skipped"),
            "news:" + ("requested-but-not-loaded" if request.include_news else "skipped"),
            "risk:deterministic-v1",
        ],
        warnings=warnings,
    )
