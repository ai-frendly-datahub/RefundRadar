from __future__ import annotations

import html
import logging
import os
import re
import threading
import time
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import structlog
from pybreaker import CircuitBreakerError
from radar_core import AdaptiveThrottler, CrawlHealthStore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import NetworkError, ParseError, SourceError
from .models import Article, Source
from .resilience import get_circuit_breaker_manager


logger = structlog.get_logger(__name__)
_log = logging.getLogger(__name__)

# Deadline extraction patterns for refund/tax/insurance deadlines
_DEADLINE_PATTERNS: list[tuple[str, str]] = [
    # Korean date patterns: ~까지, 마감, 기한
    (r"(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})[일]?", "korean_date"),
    # ISO-like: 2024-03-31, 2024.03.31, 2024/03/31
    (r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", "iso_date"),
    # Relative: ~일 이내, ~일까지
    (r"(\d{1,3})\s*일\s*(이내|까지|내)", "relative_days"),
    # Month/day Korean: 3월 31일
    (r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", "month_day_korean"),
    # English formats: March 31, 2024
    (
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),?\s*(\d{4})",
        "english_date",
    ),
]

_DEADLINE_CONTEXT_KEYWORDS: list[str] = [
    "마감",
    "기한",
    "deadline",
    "기간",
    "까지",
    "신청",
    "접수",
    "환급",
    "refund",
    "신고",
    "납부",
    "due",
    "expires",
    "expiry",
]


def extract_deadline_from_text(text: str) -> str | None:
    """Extract a deadline date from article text.

    Searches for date patterns near deadline-related keywords.

    Args:
        text: Article title or summary text.

    Returns:
        Extracted deadline string in YYYY-MM-DD format, or None.
    """
    if not text or not isinstance(text, str):
        return None

    text_lower = text.lower()

    # Check if text contains deadline context keywords
    has_context = any(kw in text_lower for kw in _DEADLINE_CONTEXT_KEYWORDS)
    if not has_context:
        return None

    for pattern_str, pattern_type in _DEADLINE_PATTERNS:
        match = re.search(pattern_str, text)
        if not match:
            continue

        try:
            if pattern_type == "korean_date" or pattern_type == "iso_date":
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if _validate_date_components(year, month, day):
                    return f"{year:04d}-{month:02d}-{day:02d}"
            elif pattern_type == "month_day_korean":
                month, day = int(match.group(1)), int(match.group(2))
                year = datetime.now(UTC).year
                if _validate_date_components(year, month, day):
                    return f"{year:04d}-{month:02d}-{day:02d}"
            elif pattern_type == "english_date":
                month_names = {
                    "january": 1,
                    "february": 2,
                    "march": 3,
                    "april": 4,
                    "may": 5,
                    "june": 6,
                    "july": 7,
                    "august": 8,
                    "september": 9,
                    "october": 10,
                    "november": 11,
                    "december": 12,
                }
                month_name = match.group(1).lower()
                month = month_names.get(month_name, 0)
                day = int(match.group(2))
                year = int(match.group(3))
                if month > 0 and _validate_date_components(year, month, day):
                    return f"{year:04d}-{month:02d}-{day:02d}"
            elif pattern_type == "relative_days":
                # For relative days, just note the relative deadline
                days = int(match.group(1))
                if 1 <= days <= 365:
                    return f"within_{days}_days"
        except (ValueError, IndexError):
            continue

    return None


def _validate_date_components(year: int, month: int, day: int) -> bool:
    """Validate date components are reasonable."""
    if year < 2000 or year > 2100:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False
    # Rough month-day validation
    max_days = {
        1: 31,
        2: 29,
        3: 31,
        4: 30,
        5: 31,
        6: 30,
        7: 31,
        8: 31,
        9: 30,
        10: 31,
        11: 30,
        12: 31,
    }
    if day > max_days.get(month, 31):
        return False
    return True


_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (compatible; RadarTemplateBot/1.0; +https://github.com/zzragida/ai-frendly-datahub)",
}
_DEFAULT_HEALTH_DB_PATH = "data/radar_data.duckdb"
_COLLECTION_CONTROL_LOCK = threading.Lock()
_ACTIVE_THROTTLER: AdaptiveThrottler | None = None
_ACTIVE_HEALTH_STORE: CrawlHealthStore | None = None


def _set_collection_controls(throttler: AdaptiveThrottler, health_store: CrawlHealthStore) -> None:
    global _ACTIVE_THROTTLER, _ACTIVE_HEALTH_STORE
    with _COLLECTION_CONTROL_LOCK:
        _ACTIVE_THROTTLER = throttler
        _ACTIVE_HEALTH_STORE = health_store


def _clear_collection_controls() -> None:
    global _ACTIVE_THROTTLER, _ACTIVE_HEALTH_STORE
    with _COLLECTION_CONTROL_LOCK:
        _ACTIVE_THROTTLER = None
        _ACTIVE_HEALTH_STORE = None


def _get_collection_controls() -> tuple[AdaptiveThrottler | None, CrawlHealthStore | None]:
    with _COLLECTION_CONTROL_LOCK:
        return _ACTIVE_THROTTLER, _ACTIVE_HEALTH_STORE


class RateLimiter:
    def __init__(self, min_interval: float = 0.5):
        self._min_interval: float = min_interval
        self._last_request: float = 0.0
        self._lock: threading.Lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request = time.monotonic()


def _resolve_max_workers(max_workers: int | None = None) -> int:
    if max_workers is None:
        raw_value = os.environ.get("RADAR_MAX_WORKERS", "5")
        try:
            parsed = int(raw_value)
        except ValueError:
            parsed = 5
    else:
        parsed = max_workers

    return max(1, min(parsed, 10))


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_DEFAULT_HEADERS)

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[408, 429, 500, 502, 503, 504, 522, 524],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def _fetch_url_with_retry(
    url: str,
    timeout: int,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    source_name: str | None = None,
    throttler: AdaptiveThrottler | None = None,
    health_store: CrawlHealthStore | None = None,
    max_attempts: int = 3,
) -> requests.Response:
    """Fetch URL with retry logic on transient errors."""
    merged = {**_DEFAULT_HEADERS, **(headers or {})}
    if throttler is None or health_store is None:
        active_throttler, active_health_store = _get_collection_controls()
        throttler = throttler or active_throttler
        health_store = health_store or active_health_store

    retryable_errors = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    )

    for attempt in range(max_attempts):
        if source_name is not None and throttler is not None:
            throttler.acquire(source_name)

        try:
            if session is not None:
                response = session.get(url, timeout=timeout, headers=merged)
            else:
                response = requests.get(url, timeout=timeout, headers=merged)
            response.raise_for_status()

            if source_name is not None and throttler is not None:
                throttler.record_success(source_name)
                if health_store is not None:
                    delay = throttler.get_current_delay(source_name)
                    health_store.record_success(source_name, delay)

            return response
        except retryable_errors as exc:
            if source_name is not None and throttler is not None:
                retry_after: int | str | None = None
                if isinstance(exc, requests.exceptions.HTTPError):
                    response = exc.response
                    if response is not None and response.status_code == 429:
                        retry_after = _parse_retry_after(response.headers.get("Retry-After"))

                throttler.record_failure(source_name, retry_after=retry_after)
                if health_store is not None:
                    delay = throttler.get_current_delay(source_name)
                    health_store.record_failure(source_name, str(exc), delay)

            if attempt == max_attempts - 1:
                raise

    raise RuntimeError("Retry loop exited unexpectedly")


def _parse_retry_after(value: str | None) -> int | str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    if stripped.isdigit():
        return int(stripped)

    return stripped


def _source_bool(source: Source, key: str) -> bool:
    value = source.config.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _source_int(source: Source, key: str, default: int) -> int:
    value = source.config.get(key)
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def collect_sources(
    sources: list[Source],
    *,
    category: str,
    limit_per_source: int = 30,
    timeout: int = 15,
    min_interval_per_host: float = 0.5,
    max_workers: int | None = None,
    health_db_path: str | None = None,
) -> tuple[list[Article], list[str]]:
    """Fetch items from all configured sources, returning articles and errors."""
    articles: list[Article] = []
    errors: list[str] = []
    enabled_sources = [source for source in sources if source.enabled]
    if not enabled_sources:
        return articles, errors

    _js_types = {"javascript", "browser", "html", "js", "web"}
    rss_sources = [source for source in enabled_sources if source.type.lower() == "rss"]
    js_sources = [source for source in enabled_sources if source.type.lower() in _js_types]
    unsupported_sources = [
        source
        for source in enabled_sources
        if source.type.lower() not in {"rss", *_js_types}
    ]

    manager = get_circuit_breaker_manager()
    workers = _resolve_max_workers(max_workers)
    resolved_health_db_path = health_db_path or os.environ.get(
        "RADAR_CRAWL_HEALTH_DB_PATH", _DEFAULT_HEALTH_DB_PATH
    )
    source_hosts: dict[str, str] = {
        source.name: (urlparse(source.url).netloc.lower() or source.name) for source in rss_sources
    }
    rate_limiters: dict[str, RateLimiter] = {
        host: RateLimiter(min_interval=min_interval_per_host) for host in set(source_hosts.values())
    }
    throttler = AdaptiveThrottler(min_delay=max(0.001, min_interval_per_host))
    health_store = CrawlHealthStore(resolved_health_db_path)
    _set_collection_controls(throttler, health_store)
    session = _create_session()

    def _collect_for_source(source: Source) -> tuple[list[Article], list[str]]:
        if (
            not _source_bool(source, "bypass_crawl_health")
            and health_store.is_disabled(source.name)
        ):
            return [], [f"{source.name}: Source disabled (crawl health threshold reached)"]

        host = source_hosts[source.name]
        rate_limiters[host].acquire()

        try:
            breaker = manager.get_breaker(source.name)
            result = breaker.call(
                _collect_single,
                source,
                category=category,
                limit=limit_per_source,
                timeout=timeout,
                session=session,
            )
            return result, []
        except CircuitBreakerError:
            return [], [f"{source.name}: Circuit breaker open (source unavailable)"]
        except SourceError as exc:
            return [], [str(exc)]
        except (NetworkError, ParseError) as exc:
            return [], [f"{source.name}: {exc}"]
        except Exception as exc:
            return [], [f"{source.name}: Unexpected error - {type(exc).__name__}: {exc}"]

    try:
        # --- Pass 1: RSS sources via ThreadPoolExecutor (parallel) ---
        if workers == 1:
            for source in rss_sources:
                source_articles, source_errors = _collect_for_source(source)
                articles.extend(source_articles)
                errors.extend(source_errors)
        else:
            if rss_sources:
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future_map: list[Future[tuple[list[Article], list[str]]]] = [
                        executor.submit(_collect_for_source, source) for source in rss_sources
                    ]

                    for future in future_map:
                        source_articles, source_errors = future.result()
                        articles.extend(source_articles)
                        errors.extend(source_errors)

        # --- Pass 2: JavaScript/browser sources via Playwright (sequential) ---
        if js_sources:
            try:
                from .browser_collector import collect_browser_sources

                js_articles, js_errors = collect_browser_sources(
                    js_sources,
                    category,
                    timeout=max(1_000, timeout * 1_000),
                    health_db_path=resolved_health_db_path,
                )
                articles.extend(js_articles)
                errors.extend(js_errors)
            except ImportError:
                logger.warning(
                    "playwright_unavailable",
                    js_source_count=len(js_sources),
                    hint="pip install 'radar-core[browser]'",
                )

        for source in unsupported_sources:
            errors.append(
                f"{source.name}: Source type '{source.type}' is cataloged but not collected by RefundRadar pipeline"
            )
            logger.warning(
                "unsupported_source_type_skipped",
                source=source.name,
                source_type=source.type,
            )
    finally:
        session.close()
        health_store.close()
        _clear_collection_controls()

    return articles, errors


def _collect_single(
    source: Source,
    *,
    category: str,
    limit: int,
    timeout: int,
    session: requests.Session | None = None,
) -> list[Article]:
    if source.type.lower() != "rss":
        logger.error(
            "unsupported_source_type",
            source=source.name,
            source_type=source.type,
        )
        raise SourceError(source.name, f"Unsupported source type '{source.type}'")

    try:
        effective_timeout = _source_int(source, "request_timeout_seconds", timeout)
        response = _fetch_url_with_retry(
            source.url,
            effective_timeout,
            session=session,
            source_name=source.name,
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        raise NetworkError(f"Network error fetching {source.name}: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise SourceError(source.name, f"Request failed: {exc}", exc) from exc

    try:
        feed = feedparser.parse(response.content)

        # Validate feed format
        if feed.bozo and feed.bozo_exception:
            logger.warning(
                "feed_parse_warning",
                source=source.name,
                bozo_exception=str(feed.bozo_exception),
            )

        items: list[Article] = []
        deadline_found_count = 0
        deadline_unparseable_count = 0

        for entry in feed.entries[:limit]:
            published = _extract_datetime(entry)
            summary = _entry_text(entry, "summary") or _entry_text(entry, "description")
            if not summary:
                _content = entry.get("content", [])
                if isinstance(_content, list) and _content:
                    first_item = _content[0]
                    if isinstance(first_item, Mapping):
                        value = first_item.get("value")
                        if isinstance(value, str):
                            summary = value

            title = html.unescape(_entry_text(entry, "title").strip()) or "(no title)"
            if not summary:
                summary = title
            link = _entry_text(entry, "link").strip()

            # Validate required fields
            if not link:
                continue

            link = urljoin(source.url, link)

            # Skip entries with invalid link format
            if not link.startswith(("http://", "https://")):
                logger.warning(
                    "skipped_invalid_link",
                    source=source.name,
                    link=link[:80],
                )
                continue

            # Attempt deadline extraction from title and summary
            combined_text = f"{title} {summary}"
            deadline = extract_deadline_from_text(combined_text)
            if deadline:
                deadline_found_count += 1
            elif any(kw in combined_text.lower() for kw in _DEADLINE_CONTEXT_KEYWORDS):
                # Text mentions deadlines but we couldn't parse the date
                deadline_unparseable_count += 1
                logger.debug(
                    "unparseable_deadline_format",
                    source=source.name,
                    title=title[:100],
                )

            # Enrich summary with extracted deadline info
            enriched_summary = html.unescape(summary.strip())
            if deadline and deadline not in enriched_summary:
                enriched_summary = f"[Deadline: {deadline}] {enriched_summary}"

            items.append(
                Article(
                    title=title,
                    link=link,
                    summary=enriched_summary,
                    published=published,
                    source=source.name,
                    category=category,
                )
            )

        if deadline_unparseable_count > 0:
            logger.warning(
                "unparseable_deadlines_summary",
                source=source.name,
                unparseable=deadline_unparseable_count,
                found=deadline_found_count,
                total=len(items),
            )

        return items
    except (ParseError, SourceError):
        raise
    except Exception as exc:
        raise ParseError(f"Failed to parse feed from {source.name}: {exc}") from exc


def _extract_datetime(entry: Mapping[str, Any]) -> datetime | None:
    """Parse a feed entry date into a timezone-aware datetime."""
    published_parsed = entry.get("published_parsed")
    if isinstance(published_parsed, time.struct_time):
        return datetime.fromtimestamp(time.mktime(published_parsed), tz=UTC)

    updated_parsed = entry.get("updated_parsed")
    if isinstance(updated_parsed, time.struct_time):
        return datetime.fromtimestamp(time.mktime(updated_parsed), tz=UTC)

    for key in ("published", "updated", "date"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(str(raw))
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except Exception:
                continue
    return None


def _entry_text(entry: Mapping[str, Any], key: str) -> str:
    value = entry.get(key)
    return value if isinstance(value, str) else ""
