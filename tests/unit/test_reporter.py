from __future__ import annotations

from datetime import UTC, datetime

from refundradar.models import Article, CategoryConfig
from refundradar.reporter import generate_report


def test_generate_report_injects_refund_quality_panel(tmp_path, monkeypatch) -> None:
    fixed_now = datetime(2026, 4, 12, 9, 30, tzinfo=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr("radar_core.report_utils.datetime", FixedDateTime)

    output_path = tmp_path / "reports" / "refund_report.html"
    category = CategoryConfig(
        category_name="refund",
        display_name="Refund",
        sources=[],
        entities=[],
    )
    article = Article(
        title="Settlement refund claim deadline",
        link="https://example.com/claim",
        summary="Claims must be submitted by April 30, 2026.",
        published=fixed_now,
        collected_at=fixed_now,
        source="Class Action Rebates",
        category="refund",
        matched_entities={"ClaimDeadline": ["2026-04-30"]},
    )
    quality_report = {
        "community_complaint_note": (
            "Community complaint_signal rows are cross-reference only."
        ),
        "summary": {
            "fresh_sources": 1,
            "stale_sources": 1,
            "missing_sources": 0,
            "refund_claim_window_events": 1,
            "recall_refund_notice_events": 1,
            "complaint_resolution_events": 1,
            "refund_policy_change_events": 0,
        },
        "sources": [
            {
                "source": "CPSC Recalls",
                "status": "stale",
                "event_model": "recall_refund_notice",
                "age_days": 3,
            }
        ],
        "events": [
            {
                "source": "Class Action Rebates",
                "event_model": "refund_claim_window",
                "title": "Settlement refund claim deadline",
                "claim_start_date": "2026-04-01",
                "claim_deadline": "2026-04-30",
                "resolution_status": [],
            },
            {
                "source": "CFPB Newsroom",
                "event_model": "complaint_resolution",
                "title": "Refund complaint resolved",
                "claim_start_date": "",
                "claim_deadline": "",
                "resolution_status": ["resolved"],
            },
        ],
    }

    generate_report(
        category=category,
        articles=[article],
        output_path=output_path,
        stats={"sources": 1, "collected": 1, "matched": 1, "window_days": 7},
        quality_report=quality_report,
    )

    html = output_path.read_text(encoding="utf-8")
    dated_html = (tmp_path / "reports" / "refund_20260412.html").read_text(
        encoding="utf-8"
    )

    for rendered in (html, dated_html):
        assert 'id="refund-quality"' in rendered
        assert "Refund Quality" in rendered
        assert "refund_quality.json" in rendered
        assert "CPSC Recalls" in rendered
        assert "Settlement refund claim deadline" in rendered
        assert "2026-04-30" in rendered
        assert "cross-reference only" in rendered
        assert not any(line.rstrip() != line for line in rendered.splitlines())

    summary = (tmp_path / "reports" / "refund_20260412_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"repo": "RefundRadar"' in summary
    assert '"ontology_version": "0.1.0"' in summary
    assert '"refund.refund_claim_window"' in summary
