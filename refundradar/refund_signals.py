from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .models import Article


_CLAIM_CONTEXT_MARKERS = (
    "claim",
    "claims",
    "submit",
    "apply",
    "deadline",
    "refund",
    "rebate",
    "settlement",
    "chargeback",
    "환급",
    "환불",
    "청구",
    "신청",
    "접수",
    "마감",
    "합의",
)
_DEADLINE_CONTEXT_MARKERS = ("deadline", "by", "until", "까지", "마감")
_YEAR_DATE_RE = re.compile(
    r"(?P<year>20\d{2})\s*(?:년|[.\-/])\s*"
    r"(?P<month>\d{1,2})\s*(?:월|[.\-/])\s*"
    r"(?P<day>\d{1,2})\s*(?:일|\.)?"
)
_MONTH_DATE_RE = re.compile(
    r"(?<!\d)(?P<month>\d{1,2})\s*(?:월|[.\-/])\s*"
    r"(?P<day>\d{1,2})\s*(?:일|\.)?"
)
_EN_MONTH_DATE_RE = re.compile(
    r"\b(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?[,]?\s+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_STATUS_KEYWORDS = {
    "refund_issued": ["refund issued", "refunds issued", "refunded", "환급", "환불", "지급"],
    "settlement_reached": ["settlement", "settled", "합의", "조정"],
    "resolved": ["resolved", "resolution", "closed", "해결", "종결", "처리"],
    "denied": ["denied", "rejected", "거절", "반려", "불가"],
    "pending": ["pending", "investigation", "reviewing", "접수", "검토", "조사"],
}


@dataclass(frozen=True)
class ClaimWindow:
    start_date: str | None
    deadline: str | None


def _reference_year(reference_date: datetime | None) -> int:
    if reference_date is None:
        return datetime.now(UTC).year
    return reference_date.year


def _iso_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(
        start < occupied_end and end > occupied_start
        for occupied_start, occupied_end in spans
    )


def _dedupe_ordered(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def extract_claim_window(text: str, *, reference_date: datetime | None = None) -> ClaimWindow:
    """Extract a conservative claim/refund window from notice text."""
    haystack = text.strip()
    haystack_lower = haystack.lower()
    if not haystack or not any(marker in haystack_lower for marker in _CLAIM_CONTEXT_MARKERS):
        return ClaimWindow(start_date=None, deadline=None)

    dates: list[str] = []
    occupied_spans: list[tuple[int, int]] = []
    for match in _YEAR_DATE_RE.finditer(haystack):
        parsed = _iso_date(
            int(match.group("year")), int(match.group("month")), int(match.group("day"))
        )
        if parsed:
            dates.append(parsed)
            occupied_spans.append(match.span())

    for match in _EN_MONTH_DATE_RE.finditer(haystack):
        month = _MONTHS[match.group("month").lower()]
        parsed = _iso_date(int(match.group("year")), month, int(match.group("day")))
        if parsed:
            dates.append(parsed)
            occupied_spans.append(match.span())

    base_year = _reference_year(reference_date)
    for match in _MONTH_DATE_RE.finditer(haystack):
        if _overlaps(match.span(), occupied_spans):
            continue
        parsed = _iso_date(base_year, int(match.group("month")), int(match.group("day")))
        if parsed:
            dates.append(parsed)

    dates = _dedupe_ordered(dates)
    if not dates:
        return ClaimWindow(start_date=None, deadline=None)
    if len(dates) >= 2:
        return ClaimWindow(start_date=dates[0], deadline=dates[-1])
    if any(marker in haystack_lower for marker in _DEADLINE_CONTEXT_MARKERS):
        return ClaimWindow(start_date=None, deadline=dates[0])
    return ClaimWindow(start_date=None, deadline=None)


def extract_resolution_status(text: str) -> list[str]:
    haystack_lower = text.lower()
    statuses: list[str] = []
    for status, keywords in _STATUS_KEYWORDS.items():
        if any(keyword.lower() in haystack_lower for keyword in keywords):
            statuses.append(status)
    return _dedupe_ordered(statuses)


def enrich_refund_operational_fields(articles: Iterable[Article]) -> list[Article]:
    """Add refund claim window and resolution status hints to matched_entities."""
    enriched: list[Article] = []
    for article in articles:
        text = f"{article.title}\n{article.summary}"
        window = extract_claim_window(text, reference_date=article.published)
        statuses = extract_resolution_status(text)

        matches = dict(article.matched_entities)
        event_models: list[str] = []
        if window.start_date:
            matches["ClaimStartDate"] = [window.start_date]
        if window.deadline:
            matches["ClaimDeadline"] = [window.deadline]
            event_models.append("refund_claim_window")
        if statuses:
            matches["ResolutionStatus"] = statuses
            event_models.append("complaint_resolution")
        if event_models:
            matches["OperationalEvent"] = _dedupe_ordered(event_models)

        article.matched_entities = matches
        enriched.append(article)
    return enriched
