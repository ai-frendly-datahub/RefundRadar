from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from refundradar.models import Article, CategoryConfig, Source
from refundradar.quality_report import build_quality_report, write_quality_report


def _source(
    name: str,
    event_model: str,
    sla_days: int | None = None,
    *,
    merge_policy: str = "",
) -> Source:
    config: dict[str, object] = {"event_model": event_model}
    if sla_days is not None:
        config["freshness_sla_days"] = sla_days
    if merge_policy:
        config["merge_policy"] = merge_policy
    return Source(name=name, type="rss", url=f"https://example.com/{name}", config=config)


def test_build_quality_report_tracks_claim_resolution_and_policy_statuses() -> None:
    now = datetime(2026, 4, 12, tzinfo=UTC)
    category = CategoryConfig(
        category_name="refund",
        display_name="Refund",
        sources=[
            _source("Claim Source", "refund_claim_window", 1),
            _source("Recall Source", "recall_refund_notice", 1),
            _source("Missing Complaint", "complaint_resolution", 2),
            _source("Policy Source", "refund_policy_change", 3),
            _source(
                "Community Source",
                "complaint_signal",
                3,
                merge_policy="cross_reference_only",
            ),
        ],
        entities=[],
    )
    articles = [
        Article(
            title="Settlement refund claim deadline",
            link="https://example.com/claim",
            summary="Claims open April 1 and close April 30, 2026.",
            published=now - timedelta(hours=6),
            collected_at=now,
            source="Claim Source",
            category="refund",
            matched_entities={
                "ClaimStartDate": ["2026-04-01"],
                "ClaimDeadline": ["2026-04-30"],
                "OperationalEvent": ["refund_claim_window"],
            },
        ),
        Article(
            title="Recall refund notice",
            link="https://example.com/recall",
            summary="Refunds are available for recalled products.",
            published=now - timedelta(days=3),
            collected_at=now,
            source="Recall Source",
            category="refund",
            matched_entities={"OperationalEvent": ["recall_refund_notice"]},
        ),
        Article(
            title="Refund policy update",
            link="https://example.com/policy",
            summary="The merchant updated refund terms.",
            published=now - timedelta(days=1),
            collected_at=now,
            source="Policy Source",
            category="refund",
            matched_entities={"OperationalEvent": ["refund_policy_change"]},
        ),
        Article(
            title="Community complaint about a refund",
            link="https://example.com/community",
            summary="A consumer says the complaint was resolved.",
            published=now,
            collected_at=now,
            source="Community Source",
            category="refund",
            matched_entities={
                "ResolutionStatus": ["resolved"],
                "OperationalEvent": ["complaint_resolution"],
            },
        ),
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        errors=["Recall Source: timeout after retry"],
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": [
                        "refund_claim_window",
                        "recall_refund_notice",
                        "complaint_resolution",
                        "refund_policy_change",
                    ]
                }
            }
        },
        generated_at=now,
    )

    assert report["summary"]["fresh_sources"] == 2
    assert report["summary"]["stale_sources"] == 1
    assert report["summary"]["missing_sources"] == 1
    assert report["summary"]["not_tracked_sources"] == 1
    assert report["summary"]["refund_claim_window_events"] == 1
    assert report["summary"]["recall_refund_notice_events"] == 1
    assert report["summary"]["complaint_resolution_events"] == 0
    assert report["summary"]["refund_policy_change_events"] == 1
    assert report["summary"]["collection_error_count"] == 1
    assert "cross-reference only" in report["community_complaint_note"]

    statuses = {row["source"]: row["status"] for row in report["sources"]}
    assert statuses == {
        "Claim Source": "fresh",
        "Recall Source": "stale",
        "Missing Complaint": "missing",
        "Policy Source": "fresh",
        "Community Source": "not_tracked",
    }

    claim_event = next(
        row for row in report["events"] if row["event_model"] == "refund_claim_window"
    )
    assert claim_event["claim_start_date"] == "2026-04-01"
    assert claim_event["claim_deadline"] == "2026-04-30"
    community_source = next(row for row in report["sources"] if row["source"] == "Community Source")
    assert community_source["merge_policy"] == "cross_reference_only"


def test_build_quality_report_excludes_disabled_sources_from_tracking_and_events() -> None:
    now = datetime(2026, 4, 12, tzinfo=UTC)
    active = _source("Active Recall", "recall_refund_notice", 7)
    disabled = Source(
        name="Disabled Recall",
        type="rss",
        url="https://example.com/disabled.xml",
        enabled=False,
        config={
            "event_model": "recall_refund_notice",
            "freshness_sla_days": 7,
            "disabled_reason": "official_feed_blocked",
            "required_before_enable": ["accessible_official_feed"],
        },
    )
    category = CategoryConfig(
        category_name="refund",
        display_name="Refund",
        sources=[active, disabled],
        entities=[],
    )
    articles = [
        Article(
            title="Active recall refund",
            link="https://example.com/active",
            summary="Refunds are available for recalled products.",
            published=now,
            collected_at=now,
            source="Active Recall",
            category="refund",
            matched_entities={"OperationalEvent": ["recall_refund_notice"]},
        ),
        Article(
            title="Disabled recall refund",
            link="https://example.com/disabled",
            summary="Refunds are available for recalled products.",
            published=now,
            collected_at=now,
            source="Disabled Recall",
            category="refund",
            matched_entities={"OperationalEvent": ["recall_refund_notice"]},
        ),
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={},
        generated_at=now,
    )

    rows = {row["source"]: row for row in report["sources"]}
    assert report["summary"]["tracked_sources"] == 1
    assert report["summary"]["skipped_disabled_sources"] == 1
    assert rows["Disabled Recall"]["tracked"] is False
    assert rows["Disabled Recall"]["status"] == "skipped_disabled"
    assert rows["Disabled Recall"]["disabled_reason"] == "official_feed_blocked"
    assert rows["Disabled Recall"]["required_before_enable"] == [
        "accessible_official_feed"
    ]
    assert [row["source"] for row in report["events"]] == ["Active Recall"]


def test_write_quality_report_writes_latest_and_dated_files(tmp_path) -> None:
    report = {
        "category": "refund",
        "generated_at": "2026-04-12T03:04:05+00:00",
        "community_complaint_note": "note",
        "summary": {},
        "sources": [],
        "events": [],
        "errors": [],
    }

    paths = write_quality_report(report, output_dir=tmp_path, category_name="refund")

    assert paths["latest"] == tmp_path / "refund_quality.json"
    assert paths["dated"] == tmp_path / "refund_20260412_quality.json"
    assert json.loads(paths["latest"].read_text(encoding="utf-8")) == report
    assert json.loads(paths["dated"].read_text(encoding="utf-8")) == report
