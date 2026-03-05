from __future__ import annotations

import time
from collections.abc import Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import cast

import feedparser
import requests

from .models import Article, Source


def collect_sources(
    sources: list[Source],
    *,
    category: str,
    limit_per_source: int = 30,
    timeout: int = 15,
) -> tuple[list[Article], list[str]]:
    """Fetch items from all configured sources, returning articles and errors."""
    articles: list[Article] = []
    errors: list[str] = []

    for source in sources:
        try:
            articles.extend(_collect_single(source, category=category, limit=limit_per_source, timeout=timeout))
        except Exception as exc:  # noqa: BLE001 - surface errors to the caller
            errors.append(f"{source.name}: {exc}")

    return articles, errors


def _collect_single(
    source: Source,
    *,
    category: str,
    limit: int,
    timeout: int,
) -> list[Article]:
    if source.type.lower() != "rss":
        raise ValueError(f"Unsupported source type '{source.type}'. Only 'rss' is supported in the template.")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; RadarBot/1.0; +https://github.com/zzragida)"}
    response = requests.get(source.url, headers=headers, timeout=timeout)
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    entries = cast(Sequence[object], feed.entries)
    items: list[Article] = []

    for raw_entry in entries[:limit]:
        entry = cast(dict[str, object], raw_entry)
        published = _extract_datetime(entry)
        summary = str(entry.get("summary") or entry.get("description") or "")
        title = str(entry.get("title") or "").strip() or "(no title)"
        link = str(entry.get("link") or "").strip()

        items.append(
            Article(
                title=title,
                link=link,
                summary=summary.strip(),
                published=published,
                source=source.name,
                category=category,
            )
        )

    return items


def _extract_datetime(entry: dict[str, object]) -> datetime | None:
    """Parse a feed entry date into a timezone-aware datetime."""
    published_parsed = entry.get("published_parsed")
    if isinstance(published_parsed, struct_time):
        return datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)
    updated_parsed = entry.get("updated_parsed")
    if isinstance(updated_parsed, struct_time):
        return datetime.fromtimestamp(time.mktime(updated_parsed), tz=timezone.utc)

    for key in ("published", "updated", "date"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(str(raw))
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return None
