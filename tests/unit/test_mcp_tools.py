from __future__ import annotations

import json
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import duckdb


SearchIndex = cast(Any, import_module("refundradar.search_index").SearchIndex)
_tools = import_module("refundradar.mcp_server.tools")
handle_search = cast(Any, _tools.handle_search)
handle_recent_updates = cast(Any, _tools.handle_recent_updates)
handle_sql = cast(Any, _tools.handle_sql)
handle_top_trends = cast(Any, _tools.handle_top_trends)
handle_case_finder = cast(Any, _tools.handle_case_finder)


def _init_articles_table(db_path: Path) -> None:
    conn = duckdb.connect(str(db_path))
    try:
        _ = conn.execute(
            """
            CREATE TABLE articles (
                id BIGINT PRIMARY KEY,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                summary TEXT,
                published TIMESTAMP,
                collected_at TIMESTAMP NOT NULL,
                entities_json TEXT
            )
            """
        )
    finally:
        conn.close()


def _seed_article(
    *,
    db_path: Path,
    article_id: int,
    title: str,
    link: str,
    collected_at: datetime,
    entities: dict[str, list[str]] | None = None,
) -> None:
    conn = duckdb.connect(str(db_path))
    try:
        _ = conn.execute(
            """
            INSERT INTO articles (id, category, source, title, link, summary, published, collected_at, entities_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                article_id,
                "refund",
                "Test Source",
                title,
                link,
                "summary",
                None,
                collected_at,
                json.dumps(entities or {}, ensure_ascii=False),
            ],
        )
    finally:
        conn.close()


def test_handle_search(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    search_db_path = tmp_path / "search.db"
    _init_articles_table(db_path)

    now = datetime.now()
    recent_link = "https://example.com/recent"
    old_link = "https://example.com/old"

    _seed_article(
        db_path=db_path,
        article_id=1,
        title="Recent refund demand",
        link=recent_link,
        collected_at=now - timedelta(days=2),
    )
    _seed_article(
        db_path=db_path,
        article_id=2,
        title="Old refund demand",
        link=old_link,
        collected_at=now - timedelta(days=20),
    )

    with SearchIndex(search_db_path) as idx:
        idx.upsert(recent_link, "Recent refund demand", "Demand is rising")
        idx.upsert(old_link, "Old refund demand", "Demand was low")

    output = handle_search(
        search_db_path=search_db_path,
        db_path=db_path,
        query="last 7 days refund",
        limit=10,
    )

    assert "Recent refund demand" in output
    assert "Old refund demand" not in output


def test_handle_recent_updates(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    _init_articles_table(db_path)
    now = datetime.now()

    _seed_article(
        db_path=db_path,
        article_id=1,
        title="Most recent",
        link="https://example.com/1",
        collected_at=now - timedelta(hours=1),
    )
    _seed_article(
        db_path=db_path,
        article_id=2,
        title="Older",
        link="https://example.com/2",
        collected_at=now - timedelta(days=2),
    )

    output = handle_recent_updates(db_path=db_path, days=1, limit=10)

    assert "Most recent" in output
    assert "Older" not in output


def test_handle_sql_select(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    _init_articles_table(db_path)

    output = handle_sql(db_path=db_path, query="SELECT COUNT(*) AS total FROM articles")

    assert "total" in output
    assert "0" in output


def test_handle_sql_blocked(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    _init_articles_table(db_path)

    output = handle_sql(db_path=db_path, query="DROP TABLE articles")

    assert "Only SELECT/WITH/EXPLAIN queries are allowed" in output


def test_handle_top_trends(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    _init_articles_table(db_path)
    now = datetime.now()

    _seed_article(
        db_path=db_path,
        article_id=1,
        title="a",
        link="https://example.com/a",
        collected_at=now - timedelta(days=1),
        entities={"Region": ["ethiopia", "kenya"], "Roaster": ["blue bottle"]},
    )
    _seed_article(
        db_path=db_path,
        article_id=2,
        title="b",
        link="https://example.com/b",
        collected_at=now - timedelta(days=1),
        entities={"Region": ["brazil"]},
    )

    output = handle_top_trends(db_path=db_path, days=7, limit=10)

    assert "Region" in output
    assert "3" in output
    assert "Roaster" in output
    assert "1" in output


def test_handle_case_finder(tmp_path: Path) -> None:
    db_path = tmp_path / "refundradar.duckdb"
    _init_articles_table(db_path)
    now = datetime.now()

    _seed_article(
        db_path=db_path,
        article_id=1,
        title="Chargeback dispute hits major platform",
        link="https://example.com/case-1",
        collected_at=now - timedelta(days=1),
        entities={"Legal": ["class action"]},
    )
    _seed_article(
        db_path=db_path,
        article_id=2,
        title="Customer support update",
        link="https://example.com/case-2",
        collected_at=now - timedelta(days=1),
    )

    output = handle_case_finder(db_path=db_path, query="chargeback", days=7, limit=10)

    assert "Found 1 case(s):" in output
    assert "Chargeback dispute hits major platform" in output
    assert "[Legal]" in output
