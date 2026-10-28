from __future__ import annotations

from unittest.mock import Mock, patch

from refundradar.collector import _collect_single
from refundradar.config_loader import load_category_config
from refundradar.models import Source


def _gate_keywords() -> list[str]:
    return [
        "환급",
        "환불",
        "보상",
        "리콜",
        "피해구제",
        "불법사금융",
        "개인정보 유출",
        "refund",
        "rebate",
        "recall",
        "settlement",
        "class action",
        "tax credit",
        "tax return",
        "IRS",
    ]


def _feed(items: list[tuple[str, str, str]]) -> bytes:
    parts = ["<?xml version='1.0' encoding='UTF-8'?>", "<rss version='2.0'><channel>"]
    for title, link, description in items:
        parts.append(
            "<item>"
            f"<title>{title}</title>"
            f"<link>{link}</link>"
            f"<description>{description}</description>"
            "<pubDate>Mon, 27 Oct 2026 12:00:00 GMT</pubDate>"
            "</item>"
        )
    parts.append("</channel></rss>")
    return "".join(parts).encode("utf-8")


def _mock_response(payload: bytes) -> Mock:
    response = Mock()
    response.content = payload
    response.raise_for_status = Mock()
    return response


def test_include_keywords_keeps_two_matches_and_blocks_two_misses() -> None:
    """Gate keeps two on-topic entries and drops two off-topic entries."""
    source = Source(
        name="Yonhap Economy",
        type="rss",
        url="https://example.com/feed",
        config={"include_keywords": _gate_keywords()},
    )
    payload = _feed(
        [
            (
                "Weekly tax briefing",
                "https://example.com/pass-summary",
                "Homeowners can claim a new TAX CREDIT this year",
            ),
            (
                "불법사금융 피해 신고가 늘었다",
                "https://example.com/pass-title",
                "금융당국이 단속 현황을 공개했다",
            ),
            (
                "Dow jumps on earnings",
                "https://example.com/block-english",
                "Investors rotate into equities after the first quiet session",
            ),
            (
                "청장, 재외동포 우선채용 협의",
                "https://example.com/block-korean",
                "정부 조직 개편으로 센터가 통합된다",
            ),
        ]
    )

    with patch("refundradar.collector.requests.get", return_value=_mock_response(payload)):
        articles = _collect_single(source, category="refund", limit=10, timeout=15)

    assert [article.title for article in articles] == [
        "Weekly tax briefing",
        "불법사금융 피해 신고가 늘었다",
    ]
    assert [article.link for article in articles] == [
        "https://example.com/pass-summary",
        "https://example.com/pass-title",
    ]


def test_source_without_include_keywords_keeps_off_topic_entries() -> None:
    source = Source(name="CPSC Recalls", type="rss", url="https://example.com/feed")
    payload = _feed(
        [
            (
                "Dow jumps on earnings",
                "https://example.com/kept",
                "Investors rotate into equities after a quiet session",
            )
        ]
    )

    with patch("refundradar.collector.requests.get", return_value=_mock_response(payload)):
        articles = _collect_single(source, category="refund", limit=10, timeout=15)

    assert len(articles) == 1
    assert articles[0].title == "Dow jumps on earnings"


def test_refund_yaml_applies_gate_and_drops_stale_sources() -> None:
    category = load_category_config("refund")
    names = {source.name for source in category.sources}
    assert "DOE Energy News" not in names
    assert "Class Action Rebates" not in names

    by_name = {source.name: source for source in category.sources}
    for name in ("TurboTax Blog", "Yonhap Economy", "MarketWatch"):
        assert by_name[name].config.get("include_keywords") == _gate_keywords()
    assert "include_keywords" not in by_name["CPSC Recalls"].config

    entities = {entity.name: entity.keywords for entity in category.entities}
    removed_stopwords = (
        "the",
        "a",
        "is",
        "are",
        "have",
        "has",
        "will",
        "can",
        "all",
        "any",
        "no",
        "i",
        "get",
        "기자",
        "뉴스",
        "오늘",
    )
    for word in removed_stopwords:
        assert word not in entities["RefundGeneral"]
    assert "원" not in entities["FinancialAmount"]
    assert "억" not in entities["FinancialAmount"]
    assert "환급" in entities["RefundGeneral"]
    assert "만원" in entities["FinancialAmount"]
