from __future__ import annotations

from importlib import import_module


def test_collect_browser_sources_forwards_source_config(monkeypatch) -> None:
    module = import_module("refundradar.browser_collector")
    article_model = import_module("refundradar.models").Article
    source = import_module("refundradar.models").Source(
        name="NY Attorney General",
        type="javascript",
        url="https://ag.ny.gov/press-releases",
        config={"wait_for": "body", "bypass_crawl_health": True},
    )
    captured: dict[str, object] = {}

    def fake_collect(*, sources, category, timeout, health_db_path):
        captured["sources"] = sources
        captured["category"] = category
        captured["timeout"] = timeout
        captured["health_db_path"] = health_db_path
        return [
            article_model(
                title="  Multi\n line \t title  ",
                link="https://example.com/article",
                summary="  Multi\n line \t summary  ",
                published=None,
                source="NY Attorney General",
                category=category,
            )
        ], []

    monkeypatch.setattr(module, "_BROWSER_COLLECTION_AVAILABLE", True)
    monkeypatch.setattr(module, "_core_collect", fake_collect)

    articles, errors = module.collect_browser_sources(
        [source],
        "refund",
        timeout=8_000,
        health_db_path="data/radar_data.duckdb",
    )

    assert len(articles) == 1
    assert articles[0].title == "Multi line title"
    assert articles[0].summary == "Multi line summary"
    assert errors == []
    assert captured["category"] == "refund"
    assert captured["timeout"] == 8_000
    assert captured["health_db_path"] == "data/radar_data.duckdb"
    assert captured["sources"] == [
        {
            "name": "NY Attorney General",
            "type": "javascript",
            "url": "https://ag.ny.gov/press-releases",
            "config": {"wait_for": "body", "bypass_crawl_health": True},
        }
    ]
