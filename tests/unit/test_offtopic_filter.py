"""Collector gates for off-topic refund feeds.

Titles in the RSS fixtures are the ones quoted in the 2026-10-29 off-topic
spec. Summaries are either empty of entity terms or another quoted title, so
the tests do not invent article text.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
from xml.sax.saxutils import escape

import yaml

from refundradar.collector import _collect_single, _keyword_in_text
from refundradar.config_loader import load_category_config
from refundradar.models import Source


def _feed(items: list[tuple[str, str, str]]) -> bytes:
    parts = ["<?xml version='1.0' encoding='UTF-8'?>", "<rss version='2.0'><channel>"]
    for title, link, description in items:
        parts.append(
            "<item>"
            f"<title>{escape(title)}</title>"
            f"<link>{escape(link)}</link>"
            f"<description>{escape(description)}</description>"
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


def _collect(source: Source, items: list[tuple[str, str, str]]) -> list[str]:
    with patch("refundradar.collector.requests.get", return_value=_mock_response(_feed(items))):
        articles = _collect_single(source, category="refund", limit=10, timeout=15)
    return [article.title for article in articles]


_NEUTRAL_SUMMARY = "No matching terms here."

_YONHAP_BOND = "국고채 금리 일제히 하락…3년물 연 3.803%"
_YONHAP_FACTORY = "한미양행, 남원에 191억 투자해 화장품·건강식품 생산공장 건립"
_YONHAP_CROWDFUND = "중기부, 제주 소상공인 24곳 참여하는 로컬 크라우드펀딩 진행"
_YONHAP_USEFUL = "당진시민 내년 설 전 30만원씩 받는다…조례안 시의회 통과"

_MW_SPLIT = "The stock market is splitting in two. Is that signaling trouble?"
_MW_AI = "Two stock picks to capitalize on Wall Street's misguided AI …"
_MW_USEFUL = "Walmart, Best Buy and other stores now use digital price tags…"

_MONEY_GOLD = "How to Buy Gold in an IRA"
_MONEY_GOLD_IRA = "8 Best Gold IRA Companies of November 2026"
_MONEY_RECESSION = "61% of Americans Think the U.S. Is in a Recession Right Now…"
_MONEY_USEFUL = "Here's How Much You'll Have to Earn in 2027 to Stop Paying Social Security…"

_NERD_MORTGAGE = "Mortgage Rates Today, Tuesday, October 27: Flat for Now"
_NERD_USEFUL = "Refinancing Student Loans With a Co-Signer: What to Know"


def test_english_plural_word_boundary_and_korean_substring() -> None:
    """ASCII keywords take a word boundary and an optional plural s.

    Korean keywords are substrings. Probes that are not quoted titles only
    check the matcher; quoted titles are copied from the spec.
    """
    recession = _MONEY_RECESSION.casefold()
    assert _keyword_in_text("recession", recession)
    assert _keyword_in_text("recession", "recessions")
    assert not _keyword_in_text("recession", "recessionary")

    assert _keyword_in_text("gold", _MONEY_GOLD.casefold())
    assert _keyword_in_text("gold", "golds")
    assert not _keyword_in_text("gold", "golden")
    assert not _keyword_in_text("suze orman", "suze")

    mortgage = _NERD_MORTGAGE.casefold()
    assert _keyword_in_text("mortgage rates", mortgage)
    assert not _keyword_in_text("mortgage rates", "mortgage ratepayers today")

    useful = _YONHAP_USEFUL.casefold()
    # 30만원 contains 만원. 받는다 does not contain the dictionary form 받다.
    assert _keyword_in_text("만원", useful)
    assert _keyword_in_text("환급", "환급금")
    assert not _keyword_in_text("받다", useful)
    bond = _YONHAP_BOND.casefold()
    assert not _keyword_in_text("환급", bond)
    assert not _keyword_in_text("만원", bond)


def test_require_entity_match_drops_quoted_noise_and_keeps_quoted_useful() -> None:
    """A small slice of the real entity lists keeps the spec's useful titles."""
    yonhap = Source(
        name="Yonhap Economy",
        type="rss",
        url="https://example.com/yonhap",
        config={"require_entity_match": True, "entity_keywords": ["만원"]},
    )
    market = Source(
        name="MarketWatch",
        type="rss",
        url="https://example.com/marketwatch",
        config={"require_entity_match": True, "entity_keywords": ["price"]},
    )

    assert _collect(
        yonhap,
        [
            (_YONHAP_BOND, "https://example.com/yonhap-bond", _NEUTRAL_SUMMARY),
            (_YONHAP_FACTORY, "https://example.com/yonhap-factory", _NEUTRAL_SUMMARY),
            (_YONHAP_CROWDFUND, "https://example.com/yonhap-crowd", _NEUTRAL_SUMMARY),
            (_YONHAP_USEFUL, "https://example.com/yonhap-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_YONHAP_USEFUL]
    assert _collect(
        market,
        [
            (_MW_SPLIT, "https://example.com/mw-split", _NEUTRAL_SUMMARY),
            (_MW_AI, "https://example.com/mw-ai", _NEUTRAL_SUMMARY),
            (_MW_USEFUL, "https://example.com/mw-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_MW_USEFUL]


def test_require_entity_match_reads_summary_as_well_as_title() -> None:
    """The bond headline has no entity term; the quoted useful line is in the summary."""
    source = Source(
        name="Yonhap Economy",
        type="rss",
        url="https://example.com/yonhap",
        config={"require_entity_match": True, "entity_keywords": ["만원"]},
    )
    assert _collect(
        source,
        [(_YONHAP_BOND, "https://example.com/yonhap-summary", _YONHAP_USEFUL)],
    ) == [_YONHAP_BOND]


def test_source_without_require_entity_match_keeps_noise_titles() -> None:
    source = Source(name="Yahoo Finance", type="rss", url="https://example.com/yahoo")
    titles = _collect(
        source,
        [
            (_YONHAP_BOND, "https://example.com/yahoo-bond", _NEUTRAL_SUMMARY),
            (_MW_SPLIT, "https://example.com/yahoo-split", _NEUTRAL_SUMMARY),
            (_MONEY_GOLD, "https://example.com/yahoo-gold", _NEUTRAL_SUMMARY),
        ],
    )
    assert titles == [_YONHAP_BOND, _MW_SPLIT, _MONEY_GOLD]


def test_require_entity_match_false_keeps_noise_titles() -> None:
    source = Source(
        name="Yonhap Economy",
        type="rss",
        url="https://example.com/yonhap",
        config={"require_entity_match": False, "entity_keywords": ["받다"]},
    )
    assert _collect(
        source,
        [(_YONHAP_BOND, "https://example.com/yonhap-off", _NEUTRAL_SUMMARY)],
    ) == [_YONHAP_BOND]


def test_exclude_title_keywords_drop_quoted_noise_and_ignore_summary() -> None:
    money = Source(
        name="Money.com",
        type="rss",
        url="https://example.com/money",
        config={"exclude_title_keywords": ["gold", "recession", "buffett", "suze orman"]},
    )
    nerd = Source(
        name="NerdWallet Finance",
        type="rss",
        url="https://example.com/nerdwallet",
        config={"exclude_title_keywords": ["mortgage rates"]},
    )

    assert _collect(
        money,
        [
            (_MONEY_GOLD, "https://example.com/money-gold", _NEUTRAL_SUMMARY),
            (_MONEY_GOLD_IRA, "https://example.com/money-gold-ira", _NEUTRAL_SUMMARY),
            (_MONEY_RECESSION, "https://example.com/money-recession", _NEUTRAL_SUMMARY),
            (_MONEY_USEFUL, "https://example.com/money-useful", _MONEY_GOLD),
        ],
    ) == [_MONEY_USEFUL]
    assert _collect(
        nerd,
        [
            (_NERD_MORTGAGE, "https://example.com/nerd-mortgage", _NEUTRAL_SUMMARY),
            (_NERD_USEFUL, "https://example.com/nerd-useful", _NERD_MORTGAGE),
        ],
    ) == [_NERD_USEFUL]


def test_source_without_exclude_title_keywords_keeps_quoted_noise() -> None:
    source = Source(name="Tax Foundation Blog", type="rss", url="https://example.com/tax")
    assert _collect(
        source,
        [
            (_MONEY_GOLD, "https://example.com/tax-gold", _NEUTRAL_SUMMARY),
            (_NERD_MORTGAGE, "https://example.com/tax-mortgage", _NEUTRAL_SUMMARY),
        ],
    ) == [_MONEY_GOLD, _NERD_MORTGAGE]


def test_include_keywords_still_run_before_entity_match() -> None:
    """Price is an entity hit, but the include gate rejects the title first."""
    source = Source(
        name="MarketWatch",
        type="rss",
        url="https://example.com/marketwatch",
        config={
            "include_keywords": ["refund"],
            "require_entity_match": True,
            "entity_keywords": ["price"],
        },
    )
    assert (
        _collect(
            source,
            [(_MW_USEFUL, "https://example.com/mw-include", _NEUTRAL_SUMMARY)],
        )
        == []
    )


def test_refund_yaml_gates_sources_without_disabling_them() -> None:
    category = load_category_config("refund")
    by_name = {source.name: source for source in category.sources}

    for name in ("Yonhap Economy", "MarketWatch", "Money.com", "NerdWallet Finance"):
        assert name in by_name

    flattened = [keyword for entity in category.entities for keyword in entity.keywords]
    for name in ("Yonhap Economy", "MarketWatch"):
        config = by_name[name].config
        assert config.get("require_entity_match") is True
        assert "include_keywords" not in config
        assert "exclude_title_keywords" not in config
        assert config.get("entity_keywords") == flattened
    assert by_name["Yonhap Economy"].config["entity_keywords"] is not (
        by_name["MarketWatch"].config["entity_keywords"]
    )

    assert by_name["Money.com"].config.get("exclude_title_keywords") == [
        "gold",
        "recession",
        "buffett",
        "suze orman",
    ]
    assert by_name["NerdWallet Finance"].config.get("exclude_title_keywords") == ["mortgage rates"]
    for name in ("Money.com", "NerdWallet Finance", "CPSC Recalls", "Yahoo Finance"):
        assert by_name[name].config.get("require_entity_match") is not True

    entities = {entity.name: entity.keywords for entity in category.entities}
    assert "환급" in entities["RefundGeneral"]
    assert "경제" in entities["Subsidy"]
    assert "만원" in entities["FinancialAmount"]
    assert "원" not in entities["FinancialAmount"]
    assert "억" not in entities["FinancialAmount"]


def test_loaded_refund_sources_filter_quoted_titles() -> None:
    """The stamped entity lists, not a hand-trimmed subset, decide the spec titles."""
    category = load_category_config("refund")
    by_name = {source.name: source for source in category.sources}

    assert _collect(
        by_name["Yonhap Economy"],
        [
            (_YONHAP_BOND, "https://example.com/live-yonhap-bond", _NEUTRAL_SUMMARY),
            (_YONHAP_FACTORY, "https://example.com/live-yonhap-factory", _NEUTRAL_SUMMARY),
            (_YONHAP_CROWDFUND, "https://example.com/live-yonhap-crowd", _NEUTRAL_SUMMARY),
            (_YONHAP_USEFUL, "https://example.com/live-yonhap-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_YONHAP_USEFUL]
    assert _collect(
        by_name["MarketWatch"],
        [
            (_MW_SPLIT, "https://example.com/live-mw-split", _NEUTRAL_SUMMARY),
            (_MW_AI, "https://example.com/live-mw-ai", _NEUTRAL_SUMMARY),
            (_MW_USEFUL, "https://example.com/live-mw-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_MW_USEFUL]
    assert _collect(
        by_name["Money.com"],
        [
            (_MONEY_GOLD, "https://example.com/live-money-gold", _NEUTRAL_SUMMARY),
            (_MONEY_GOLD_IRA, "https://example.com/live-money-ira", _NEUTRAL_SUMMARY),
            (_MONEY_RECESSION, "https://example.com/live-money-recession", _NEUTRAL_SUMMARY),
            (_MONEY_USEFUL, "https://example.com/live-money-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_MONEY_USEFUL]
    assert _collect(
        by_name["NerdWallet Finance"],
        [
            (_NERD_MORTGAGE, "https://example.com/live-nerd-mortgage", _NEUTRAL_SUMMARY),
            (_NERD_USEFUL, "https://example.com/live-nerd-useful", _NEUTRAL_SUMMARY),
        ],
    ) == [_NERD_USEFUL]


def test_explicit_false_flag_is_not_stamped(tmp_path: Path) -> None:
    config_dir = tmp_path / "categories"
    config_dir.mkdir()
    _ = (config_dir / "sample.yaml").write_text(
        yaml.safe_dump(
            {
                "category_name": "sample",
                "display_name": "Sample",
                "sources": [
                    {
                        "name": "Open Wire",
                        "type": "rss",
                        "url": "https://example.com/open",
                        "require_entity_match": False,
                    }
                ],
                "entities": [
                    {"name": "RefundType", "display_name": "환급", "keywords": ["환급"]},
                ],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    category = load_category_config("sample", categories_dir=config_dir)
    source = category.sources[0]
    assert source.config.get("require_entity_match") is False
    assert "entity_keywords" not in source.config
