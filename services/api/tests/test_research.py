from app.research.models import ResearchRequest
from app.research.service import build_research_report


def test_research_report_is_advisory_and_traceable() -> None:
    report = build_research_report(
        ResearchRequest(symbol="RELIANCE"),
        {
            "ltp": 2942.40,
            "change_pct": 1.84,
            "volume": 8420000,
            "rsi": 64.2,
            "score": 86,
        },
    )

    assert report.decision == "paper_candidate"
    assert report.order_authority == "none"
    assert report.approval_required is True
    assert report.evidence[0].status == "demo"
    assert "technical:deterministic-v1" in report.agent_trace
    assert report.warnings


def test_unknown_symbol_does_not_fake_available_evidence() -> None:
    report = build_research_report(
        ResearchRequest(symbol="UNKNOWN"),
        None,
    )

    assert report.decision == "watch"
    assert report.data_quality == "demo"
    assert report.evidence[0].status == "not_loaded"
    assert any("not present" in warning for warning in report.warnings)
