"""Item URLs must be each entry's own absolute page, not the feed or index."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

from refundradar.collector import _collect_single
from refundradar.config_loader import load_category_config
from refundradar.models import Article, Source


def _collect(payload: str, url: str) -> list[Article]:
    source = Source(name="Example Feed", type="rss", url=url)
    response = Mock()
    response.content = payload.encode("utf-8")
    response.raise_for_status = Mock()
    with patch("refundradar.collector.requests.get", return_value=response):
        return _collect_single(source, category="refund", limit=10, timeout=5)


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "freakonomics_radio.xml"
_FEED_URL = "https://feeds.simplecast.com/Y8lFbOT4"
_SHOW_HOME = "https://freakonomics.com"


def test_refund_config_keeps_freakonomics_public_feed() -> None:
    category = load_category_config("refund")
    source = next(item for item in category.sources if item.name == "Freakonomics Radio")
    assert source.type == "rss"
    assert source.url == _FEED_URL


def test_freakonomics_fixture_uses_each_enclosure_instead_of_the_show_index() -> None:
    """Public-feed excerpt: every item link is the show home, guid is not a permalink."""
    root = ET.fromstring(_FIXTURE.read_bytes())
    items = [element for element in root.iter() if _local(element.tag) == "item"]
    assert len(items) == 2

    expected: list[str] = []
    for item in items:
        link = next(child for child in list(item) if _local(child.tag) == "link")
        guid = next(child for child in list(item) if _local(child.tag) == "guid")
        enclosure = next(child for child in list(item) if _local(child.tag) == "enclosure")
        assert (link.text or "").strip() == _SHOW_HOME
        assert guid.attrib["isPermaLink"] == "false"
        assert enclosure.attrib["type"] == "audio/mpeg"
        expected.append(enclosure.attrib["url"])

    source = Source(name="Freakonomics Radio", type="rss", url=_FEED_URL)
    response = Mock()
    response.content = _FIXTURE.read_bytes()
    response.raise_for_status = Mock()
    with patch("refundradar.collector.requests.get", return_value=response):
        articles = _collect_single(source, category="refund", limit=10, timeout=5)

    assert [article.link for article in articles] == expected
    assert len(set(expected)) == 2
    assert _SHOW_HOME not in expected
    assert _FEED_URL not in expected
    assert [article.title for article in articles] == [
        "692. What Will A.I. Do to (and for) Human Creativity?",
        "Are Private Equity Firms Plundering the U.S. Economy? (Update)",
    ]


def test_explicit_article_link_wins_over_permalink_guid_and_enclosure() -> None:
    payload = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <link>https://www.cpsc.gov/</link>
      <item>
        <title>Recall notice</title>
        <link>https://www.cpsc.gov/Recalls/2026/Example</link>
        <guid isPermaLink="true">https://www.cpsc.gov/_internal</guid>
        <enclosure url="https://cdn.example.com/recall.mp3" type="audio/mpeg"/>
      </item>
    </channel></rss>"""
    articles = _collect(payload, "https://www.cpsc.gov/Newsroom/CPSC-RSS-Feed/Recalls-RSS")
    assert [article.link for article in articles] == ["https://www.cpsc.gov/Recalls/2026/Example"]


def test_relative_link_is_resolved_against_the_feed_url() -> None:
    payload = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <link>https://news.example.com/</link>
      <item>
        <title>Relative article</title>
        <link>articles/refund.html</link>
      </item>
      <item>
        <title>Root relative article</title>
        <link>/briefs/tax-credit.html</link>
      </item>
    </channel></rss>"""
    articles = _collect(payload, "https://news.example.com/rss/feed.xml")
    assert [article.link for article in articles] == [
        "https://news.example.com/rss/articles/refund.html",
        "https://news.example.com/briefs/tax-credit.html",
    ]


def test_feed_page_link_falls_through_to_permalink_guid() -> None:
    payload = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <link>https://news.example.com/rss/feed.xml</link>
      <item>
        <title>Feed page link</title>
        <link>https://news.example.com/rss/feed.xml</link>
        <guid isPermaLink="true">https://news.example.com/articles/3</guid>
      </item>
      <item>
        <title>Missing link</title>
        <guid>https://news.example.com/articles/4</guid>
      </item>
      <item>
        <title>Relative permalink</title>
        <guid isPermaLink="true">articles/5</guid>
      </item>
    </channel></rss>"""
    articles = _collect(payload, "https://news.example.com/rss/feed.xml")
    assert [article.link for article in articles] == [
        "https://news.example.com/articles/3",
        "https://news.example.com/articles/4",
        "https://news.example.com/rss/articles/5",
    ]


def test_non_permalink_guid_does_not_replace_an_enclosure_page() -> None:
    payload = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <link>https://show.example/</link>
      <item>
        <title>Enclosure page</title>
        <guid isPermaLink="false">https://show.example/not-a-permalink</guid>
        <enclosure url="https://cdn.example.com/episode.mp3" type="audio/mpeg" length="1"/>
        <enclosure url="https://show.example/episodes/page" type="text/html" length="1"/>
      </item>
      <item>
        <title>No usable url</title>
        <guid isPermaLink="false">opaque-id</guid>
      </item>
    </channel></rss>"""
    articles = _collect(payload, "https://show.example/feed.xml")
    assert [article.title for article in articles] == ["Enclosure page"]
    assert articles[0].link == "https://show.example/episodes/page"


def test_second_link_is_used_when_the_first_is_only_the_index() -> None:
    payload = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <link>https://news.example.com/</link>
      <item>
        <title>Two links</title>
        <link>https://news.example.com/</link>
        <link>https://news.example.com/articles/real</link>
      </item>
    </channel></rss>"""
    articles = _collect(payload, "https://news.example.com/rss/feed.xml")
    assert [article.link for article in articles] == ["https://news.example.com/articles/real"]
