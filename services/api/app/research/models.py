from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ResearchTimeframe = Literal["5m", "15m", "1h", "4h", "1d", "1w", "1M", "1Y"]
ResearchMode = Literal["demo", "paper", "connected"]
EvidenceStatus = Literal["demo", "available", "not_loaded"]


class ResearchRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    timeframe: ResearchTimeframe = "1d"
    universe: str = Field(default="nifty50", min_length=1, max_length=40)
    include_news: bool = True
    include_fundamentals: bool = True


class ResearchEvidence(BaseModel):
    id: str
    role: str
    source: str
    as_of: str
    status: EvidenceStatus
    summary: str
    values: dict[str, float | str | None] = Field(default_factory=dict)


class ResearchFinding(BaseModel):
    role: str
    title: str
    conclusion: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    report_id: str
    symbol: str
    timeframe: ResearchTimeframe
    universe: str
    mode: ResearchMode
    data_quality: EvidenceStatus
    as_of: str
    decision: Literal["watch", "paper_candidate", "no_trade"]
    confidence: float = Field(ge=0, le=1)
    summary: str
    findings: list[ResearchFinding]
    evidence: list[ResearchEvidence]
    risks: list[str]
    next_actions: list[str]
    agent_trace: list[str]
    order_authority: Literal["none"] = "none"
    approval_required: bool = True
    warnings: list[str] = Field(default_factory=list)
