from __future__ import annotations

import pytest

from refundradar.models import Article, Source
from refundradar.relevance import apply_source_context_entities, filter_relevant_articles


pytestmark = pytest.mark.unit


def _article(
    *,
    title: str,
    source: str = "CPSC Recalls",
    summary: str | None = None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=f"https://example.com/{title}",
        summary=summary if summary is not None else title,
        published=None,
        source=source,
        category="refund",
        matched_entities=matched_entities or {},
    )


def test_apply_source_context_entities_adds_event_model_signal() -> None:
    article = _article(
        title="Product recall refund notice",
        matched_entities={"ConsumerProtection": ["recall"]},
    )
    source = Source(
        name="CPSC Recalls",
        type="rss",
        url="https://www.cpsc.gov/recalls",
        info_purpose=["recall_refund_notice"],
        config={"event_model": "recall_refund_notice"},
    )

    classified = apply_source_context_entities([article], [source])

    assert classified[0].matched_entities["SourceSignal"] == ["recall_refund_notice"]


def test_filter_relevant_articles_keeps_refund_rows_and_drops_generic_finance() -> None:
    sources = [
        Source(
            name="CPSC Recalls",
            type="rss",
            url="https://www.cpsc.gov/recalls",
            config={"event_model": "recall_refund_notice"},
        ),
        Source(name="MarketWatch", type="rss", url="https://example.com/marketwatch"),
        Source(name="Yonhap Economy", type="rss", url="https://example.com/yonhap"),
    ]
    articles = [
        _article(
            title="Battery pack recalled due to burn hazard",
            matched_entities={"ConsumerProtection": ["recall"]},
        ),
        _article(
            title="Taxpayers can claim child tax credit by April 15",
            source="MarketWatch",
            matched_entities={
                "TaxBenefit": ["tax credit"],
                "Eligibility": ["deadline"],
            },
        ),
        _article(
            title="미국-이란 협상 결렬에 증시 하락",
            source="Yonhap Economy",
            matched_entities={"RefundGeneral": ["기자", "뉴스"]},
        ),
    ]

    filtered = filter_relevant_articles(
        apply_source_context_entities(articles, sources),
        sources,
    )

    assert [article.title for article in filtered] == [
        "Battery pack recalled due to burn hazard",
        "Taxpayers can claim child tax credit by April 15",
    ]


def test_filter_relevant_articles_drops_browser_index_chrome() -> None:
    source = Source(
        name="식품의약품안전처 리콜",
        type="javascript",
        url="https://www.mfds.go.kr/",
        config={"event_model": "recall_refund_notice"},
    )
    article = _article(
        title="식품의약품안전처>법령/자료>홍보물자료",
        source="식품의약품안전처 리콜",
        summary="본문 바로가기 주메뉴 바로가기 국민소통 알림 법령/자료",
        matched_entities={
            "ConsumerProtection": ["리콜"],
            "RefundType": ["환급"],
            "OperationalEvent": ["recall_refund_notice"],
        },
    )

    assert filter_relevant_articles([article], [source]) == []


def test_filter_relevant_articles_drops_generic_settlement_market_news() -> None:
    source = Source(name="Yonhap Economy", type="rss", url="https://example.com/yonhap")
    article = _article(
        title="구윤철 \"2주 휴전 합의했지만 상황예단 어렵다\"",
        source="Yonhap Economy",
        summary="중동 전쟁에 관해 최근 2주 휴전에 합의했으나 향후 상황을 예단하기 어렵다고 밝혔다.",
        matched_entities={"ConsumerProtection": ["합의"], "RefundGeneral": ["뉴스"]},
    )

    assert filter_relevant_articles([article], [source]) == []


def test_filter_relevant_articles_keeps_consumer_dispute_resolution() -> None:
    source = Source(name="Yonhap Economy", type="rss", url="https://example.com/yonhap")
    article = _article(
        title="소비자분쟁조정위, 쿠팡 개인정보유출 집단분쟁조정 절차 개시",
        source="Yonhap Economy",
        matched_entities={"ConsumerProtection": ["소비자"], "RefundGeneral": ["뉴스"]},
    )

    assert filter_relevant_articles([article], [source]) == [article]


def test_filter_relevant_articles_keeps_official_complaint_resolution_title_signal() -> None:
    source = Source(
        name="NY Attorney General",
        type="javascript",
        url="https://ag.ny.gov/press-releases",
        trust_tier="T1_official",
        config={"event_model": "complaint_resolution"},
    )
    article = _article(
        title="Attorney General secures settlement with retailer for cheating consumers",
        source="NY Attorney General",
        matched_entities={},
    )

    assert filter_relevant_articles([article], [source]) == [article]


def test_filter_relevant_articles_keeps_official_penalty_title_signal() -> None:
    source = Source(
        name="Australia ACCC",
        type="rss",
        url="https://www.accc.gov.au/rss/news_centre.xml",
        trust_tier="T1_official",
        config={"event_model": "complaint_resolution"},
    )
    article = _article(
        title=(
            "Bedding supplier Emma Sleep to pay a total of $15m in penalties "
            "for misleading statements about sale prices"
        ),
        source="Australia ACCC",
        matched_entities={},
    )

    assert filter_relevant_articles([article], [source]) == [article]


def test_filter_relevant_articles_keeps_official_tax_claim_window_title_signal() -> None:
    source = Source(
        name="IRS Newsroom",
        type="javascript",
        url="https://www.irs.gov/newsroom",
        trust_tier="T1_official",
        config={"event_model": "refund_claim_window"},
    )
    article = _article(
        title="Act now to file, pay, or request an extension",
        source="IRS Newsroom",
        matched_entities={},
    )

    assert filter_relevant_articles([article], [source]) == [article]


def test_filter_relevant_articles_drops_tax_product_promo_without_refund_signal() -> None:
    source = Source(name="TurboTax Blog", type="rss", url="https://example.com/turbotax")
    article = _article(
        title="Intuit TurboTax is Now Live on Claude and Better Than Ever with App in ChatGPT",
        source="TurboTax Blog",
        summary="Your tax questions deserve expert-backed AI Tax season has always come with one big question.",
        matched_entities={"TaxBenefit": ["tax season", "tax", "turbotax"]},
    )

    assert filter_relevant_articles([article], [source]) == []


def test_filter_relevant_articles_keeps_tax_refund_signal() -> None:
    source = Source(name="TurboTax Blog", type="rss", url="https://example.com/turbotax")
    article = _article(
        title="Why Everyone Is Talking About Bigger Refunds",
        source="TurboTax Blog",
        summary="IRS data shows average refunds are up.",
        matched_entities={"RefundType": ["refund"], "TaxBenefit": ["irs", "tax"]},
    )

    assert filter_relevant_articles([article], [source]) == [article]


def test_filter_relevant_articles_drops_korean_reporting_center_noise() -> None:
    source = Source(name="Yonhap Economy", type="rss", url="https://example.com/yonhap")
    article = _article(
        title="강동구, 유가 급등에 주유소 현장점검…매점매석 신고센터 운영",
        source="Yonhap Economy",
        matched_entities={"TaxBenefit": ["신고"], "Eligibility": ["대상"]},
    )

    assert filter_relevant_articles([article], [source]) == []
