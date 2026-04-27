from __future__ import annotations

from datetime import UTC, datetime

from refundradar.models import Article
from refundradar.refund_signals import (
    enrich_refund_operational_fields,
    extract_claim_window,
    extract_resolution_status,
)


def test_extract_claim_window_with_korean_year_range() -> None:
    window = extract_claim_window(
        "환불 신청은 2026년 4월 1일부터 2026년 4월 30일까지 접수",
        reference_date=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert window.start_date == "2026-04-01"
    assert window.deadline == "2026-04-30"


def test_extract_claim_window_with_english_deadline() -> None:
    window = extract_claim_window(
        "Settlement claims must be submitted by April 30, 2026.",
        reference_date=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert window.start_date is None
    assert window.deadline == "2026-04-30"


def test_extract_claim_window_does_not_guess_without_claim_context() -> None:
    window = extract_claim_window(
        "The agency published a report on April 30, 2026.",
        reference_date=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert window.start_date is None
    assert window.deadline is None


def test_extract_resolution_status_maps_refund_and_resolution_terms() -> None:
    statuses = extract_resolution_status("Refund issued after the complaint was resolved.")

    assert statuses == ["refund_issued", "resolved"]


def test_enrich_refund_operational_fields_adds_matched_entities() -> None:
    article = Article(
        title="Settlement refund claim deadline",
        link="https://example.com/refund",
        summary="Claims must be submitted by April 30, 2026. Refund issued after resolution.",
        published=datetime(2026, 4, 1, tzinfo=UTC),
        source="Class Action Rebates",
        category="refund",
        matched_entities={"RefundType": ["refund"]},
    )

    enriched = enrich_refund_operational_fields([article])[0]

    assert enriched.matched_entities["ClaimDeadline"] == ["2026-04-30"]
    assert enriched.matched_entities["ResolutionStatus"] == [
        "refund_issued",
        "settlement_reached",
        "resolved",
    ]
    assert enriched.matched_entities["OperationalEvent"] == [
        "refund_claim_window",
        "complaint_resolution",
    ]
