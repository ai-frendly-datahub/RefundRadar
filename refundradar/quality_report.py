from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Article, CategoryConfig, Source


TRACKED_EVENT_MODEL_ORDER = [
    "refund_claim_window",
    "recall_refund_notice",
    "complaint_resolution",
    "refund_policy_change",
]
TRACKED_EVENT_MODELS = set(TRACKED_EVENT_MODEL_ORDER)


def build_quality_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    errors: Iterable[str] | None = None,
    quality_config: Mapping[str, object] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = _as_utc(generated_at or datetime.now(UTC))
    articles_list = list(articles)
    errors_list = [str(error) for error in (errors or [])]
    quality = _dict(quality_config or {}, "data_quality")
    freshness_sla = _dict(quality, "freshness_sla")
    tracked_event_models = _tracked_event_models(quality)

    source_rows = [
        _build_source_row(
            source=source,
            articles=articles_list,
            errors=errors_list,
            freshness_sla=freshness_sla,
            tracked_event_models=tracked_event_models,
            generated_at=generated,
        )
        for source in category.sources
    ]
    events = _build_event_rows(
        sources=category.sources,
        articles=articles_list,
        tracked_event_models=tracked_event_models,
        freshness_sla=freshness_sla,
        generated_at=generated,
    )

    status_counts = Counter(str(row["status"]) for row in source_rows)
    event_counts = Counter(str(row["event_model"]) for row in events)
    event_status_counts = Counter(str(row["event_status"]) for row in events)
    event_keys = {
        str(row["refund_event_key"])
        for row in events
        if str(row.get("refund_event_key") or "")
    }
    summary = {
        "total_sources": len(source_rows),
        "tracked_sources": sum(1 for row in source_rows if row["tracked"]),
        "fresh_sources": status_counts.get("fresh", 0),
        "stale_sources": status_counts.get("stale", 0),
        "missing_sources": status_counts.get("missing", 0),
        "unknown_event_date_sources": status_counts.get("unknown_event_date", 0),
        "not_tracked_sources": status_counts.get("not_tracked", 0),
        "skipped_disabled_sources": status_counts.get("skipped_disabled", 0),
        "collection_error_count": len(errors_list),
        "fresh_refund_events": event_status_counts.get("fresh", 0),
        "stale_refund_events": event_status_counts.get("stale", 0),
        "undated_refund_events": event_status_counts.get("unknown_event_date", 0),
        "unique_refund_event_key_count": len(event_keys),
        "events_with_evidence_url": sum(1 for row in events if row.get("evidence_url")),
        "refund_claim_window_events_with_deadline": sum(
            1
            for row in events
            if row.get("event_model") == "refund_claim_window"
            and row.get("claim_deadline")
        ),
        "complaint_resolution_events_with_status": sum(
            1
            for row in events
            if row.get("event_model") == "complaint_resolution"
            and row.get("resolution_status")
        ),
        "refund_policy_change_events_with_effective_date": sum(
            1
            for row in events
            if row.get("event_model") == "refund_policy_change"
            and row.get("policy_effective_date")
        ),
    }
    for event_model in TRACKED_EVENT_MODEL_ORDER:
        summary[f"{event_model}_events"] = event_counts.get(event_model, 0)
    daily_review_items = _build_daily_review_items(
        source_rows=source_rows,
        events=events,
    )
    summary["daily_review_item_count"] = len(daily_review_items)

    return {
        "category": category.category_name,
        "generated_at": generated.isoformat(),
        "community_complaint_note": (
            "Community complaint_signal rows are cross-reference only and do not "
            "replace official complaint_resolution evidence."
        ),
        "summary": summary,
        "sources": source_rows,
        "events": events,
        "daily_review_items": daily_review_items,
        "errors": errors_list,
    }


def write_quality_report(
    report: dict[str, Any],
    *,
    output_dir: Path,
    category_name: str,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = _parse_datetime(str(report.get("generated_at") or "")) or datetime.now(UTC)
    date_stamp = _as_utc(generated_at).strftime("%Y%m%d")

    latest_path = output_dir / f"{category_name}_quality.json"
    dated_path = output_dir / f"{category_name}_{date_stamp}_quality.json"
    encoded = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    latest_path.write_text(encoded + "\n", encoding="utf-8")
    dated_path.write_text(encoded + "\n", encoding="utf-8")
    return {"latest": latest_path, "dated": dated_path}


def _build_source_row(
    *,
    source: Source,
    articles: list[Article],
    errors: list[str],
    freshness_sla: Mapping[str, object],
    tracked_event_models: set[str],
    generated_at: datetime,
) -> dict[str, Any]:
    source_articles = [article for article in articles if article.source == source.name]
    source_errors = _source_errors(source.name, errors)
    event_model = _source_event_model(source)
    tracked = _is_tracked_source(source, event_model, tracked_event_models)
    latest_article = _latest_article(source_articles)
    latest_event_at = _event_datetime(latest_article, source) if latest_article else None
    sla_days = _source_sla_days(source, event_model, freshness_sla)
    age_days = _age_days(generated_at, latest_event_at) if latest_event_at else None
    status = _source_status(
        source=source,
        tracked=tracked,
        article_count=len(source_articles),
        latest_event_at=latest_event_at,
        sla_days=sla_days,
        age_days=age_days,
    )

    matched = latest_article.matched_entities if latest_article else {}
    return {
        "source": source.name,
        "source_type": source.type,
        "enabled": source.enabled,
        "tracked": tracked,
        "event_model": event_model,
        "freshness_sla_days": sla_days,
        "status": status,
        "article_count": len(source_articles),
        "latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
        "age_days": round(age_days, 2) if age_days is not None else None,
        "latest_title": latest_article.title if latest_article else "",
        "latest_url": latest_article.link if latest_article else "",
        "latest_claim_start_date": _first(matched, "ClaimStartDate"),
        "latest_claim_deadline": _first(matched, "ClaimDeadline"),
        "latest_resolution_status": _list(matched.get("ResolutionStatus")),
        "latest_operational_events": _list(matched.get("OperationalEvent")),
        "merge_policy": str(source.config.get("merge_policy") or ""),
        "disabled_reason": str(source.config.get("disabled_reason") or "").strip(),
        "required_before_enable": _list(source.config.get("required_before_enable")),
        "errors": source_errors,
    }


def _build_event_rows(
    *,
    sources: list[Source],
    articles: list[Article],
    tracked_event_models: set[str],
    freshness_sla: Mapping[str, object],
    generated_at: datetime,
) -> list[dict[str, Any]]:
    sources_by_name = {source.name: source for source in sources}
    rows: list[dict[str, Any]] = []
    for article in articles:
        source = sources_by_name.get(article.source)
        if source is None:
            continue
        if not source.enabled:
            continue
        event_models = _article_event_models(article, source, tracked_event_models)
        if not event_models:
            continue
        for event_model in event_models:
            event_at = _refund_event_datetime(article, source, event_model)
            sla_days = _source_sla_days(source, event_model, freshness_sla)
            age_days = _age_days(generated_at, event_at) if event_at else None
            rows.append(
                {
                    "source": source.name,
                    "event_model": event_model,
                    "title": article.title,
                    "url": article.link,
                    "event_at": event_at.isoformat() if event_at else None,
                    "event_age_days": round(age_days, 2) if age_days is not None else None,
                    "event_freshness_sla_days": sla_days,
                    "event_status": _event_status(
                        event_at=event_at,
                        age_days=age_days,
                        sla_days=sla_days,
                    ),
                    "refund_event_key": _refund_event_key(
                        article=article,
                        source=source,
                        event_model=event_model,
                    ),
                    "claim_start_date": _first(article.matched_entities, "ClaimStartDate"),
                    "claim_deadline": _first(article.matched_entities, "ClaimDeadline"),
                    "resolution_status": _list(article.matched_entities.get("ResolutionStatus")),
                    "policy_effective_date": _first(article.matched_entities, "PolicyEffectiveDate")
                    or _first(article.matched_entities, "EffectiveDate"),
                    "evidence_url": article.link,
                    "evidence_url_present": bool(article.link),
                    "merge_policy": str(source.config.get("merge_policy") or ""),
                }
            )
    return rows


def _build_daily_review_items(
    *,
    source_rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in source_rows:
        source_name = str(row.get("source") or "")
        status = str(row.get("status") or "")
        event_model = str(row.get("event_model") or "")
        if status in {"missing", "stale", "unknown_event_date"}:
            items.append(
                {
                    "reason": f"source_status_{status}",
                    "source": source_name,
                    "event_model": event_model,
                    "freshness_sla_days": row.get("freshness_sla_days"),
                    "age_days": row.get("age_days"),
                    "latest_event_at": row.get("latest_event_at"),
                    "detail": "Tracked refund source needs collection or freshness follow-up.",
                }
            )

        if status == "skipped_disabled" and event_model in TRACKED_EVENT_MODELS:
            items.append(
                {
                    "reason": "disabled_source_gate",
                    "source": source_name,
                    "event_model": event_model,
                    "disabled_reason": row.get("disabled_reason"),
                    "required_before_enable": row.get("required_before_enable", []),
                }
            )

        for error in _list(row.get("errors")):
            items.append(
                {
                    "reason": "source_collection_error",
                    "source": source_name,
                    "event_model": event_model,
                    "error": error,
                }
            )

    for event in events:
        event_model = str(event.get("event_model") or "")
        event_status = str(event.get("event_status") or "")
        if event_status in {"stale", "unknown_event_date"}:
            items.append(
                {
                    "reason": f"event_status_{event_status}",
                    "source": event.get("source"),
                    "event_model": event_model,
                    "event_at": event.get("event_at"),
                    "event_age_days": event.get("event_age_days"),
                    "event_freshness_sla_days": event.get("event_freshness_sla_days"),
                    "evidence_url": event.get("evidence_url"),
                    "title": event.get("title"),
                }
            )
        if not event.get("evidence_url"):
            items.append(
                {
                    "reason": "event_missing_evidence_url",
                    "source": event.get("source"),
                    "event_model": event_model,
                    "title": event.get("title"),
                }
            )
        if event_model == "refund_claim_window" and not event.get("claim_deadline"):
            items.append(
                {
                    "reason": "claim_window_missing_deadline",
                    "source": event.get("source"),
                    "event_model": event_model,
                    "refund_event_key": event.get("refund_event_key"),
                    "evidence_url": event.get("evidence_url"),
                    "title": event.get("title"),
                }
            )
        if event_model == "complaint_resolution" and not event.get("resolution_status"):
            items.append(
                {
                    "reason": "complaint_resolution_missing_status",
                    "source": event.get("source"),
                    "event_model": event_model,
                    "refund_event_key": event.get("refund_event_key"),
                    "evidence_url": event.get("evidence_url"),
                    "title": event.get("title"),
                }
            )
        if event_model == "refund_policy_change" and not event.get("policy_effective_date"):
            items.append(
                {
                    "reason": "policy_change_missing_effective_date",
                    "source": event.get("source"),
                    "event_model": event_model,
                    "refund_event_key": event.get("refund_event_key"),
                    "evidence_url": event.get("evidence_url"),
                    "title": event.get("title"),
                }
            )

    return items[:100]


def _article_event_models(
    article: Article,
    source: Source,
    tracked_event_models: set[str],
) -> list[str]:
    if _is_cross_reference_only(source):
        return []

    values: set[str] = set()
    source_event_model = _source_event_model(source)
    if source_event_model in tracked_event_models:
        values.add(source_event_model)
    for event_model in _list(article.matched_entities.get("OperationalEvent")):
        if event_model in tracked_event_models:
            values.add(event_model)
    return [event_model for event_model in TRACKED_EVENT_MODEL_ORDER if event_model in values]


def _is_tracked_source(
    source: Source,
    event_model: str,
    tracked_event_models: set[str],
) -> bool:
    return (
        source.enabled
        and event_model in tracked_event_models
        and not _is_cross_reference_only(source)
    )


def _source_status(
    *,
    source: Source,
    tracked: bool,
    article_count: int,
    latest_event_at: datetime | None,
    sla_days: int | None,
    age_days: float | None,
) -> str:
    if not source.enabled:
        return "skipped_disabled"
    if not tracked:
        return "not_tracked"
    if article_count == 0:
        return "missing"
    if latest_event_at is None or age_days is None:
        return "unknown_event_date"
    if sla_days is not None and age_days > sla_days:
        return "stale"
    return "fresh"


def _tracked_event_models(quality: Mapping[str, object]) -> set[str]:
    outputs = _dict(quality, "quality_outputs")
    output_models = _string_set(outputs.get("tracked_event_models"))
    if output_models:
        return output_models & TRACKED_EVENT_MODELS or set(TRACKED_EVENT_MODELS)
    configured_models = _string_set(quality.get("event_models"))
    return configured_models & TRACKED_EVENT_MODELS or set(TRACKED_EVENT_MODELS)


def _source_event_model(source: Source) -> str:
    raw = source.config.get("event_model")
    return str(raw).strip() if raw is not None else ""


def _is_cross_reference_only(source: Source) -> bool:
    return str(source.config.get("merge_policy") or "").strip() == "cross_reference_only"


def _source_sla_days(
    source: Source,
    event_model: str,
    freshness_sla: Mapping[str, object],
) -> int | None:
    raw_source_sla = source.config.get("freshness_sla_days")
    parsed_source_sla = _as_int(raw_source_sla)
    if parsed_source_sla is not None:
        return parsed_source_sla
    model_sla = freshness_sla.get(event_model)
    if isinstance(model_sla, Mapping):
        return _as_int(model_sla.get("max_age_days"))
    return None


def _latest_article(articles: list[Article]) -> Article | None:
    dated: list[tuple[datetime, Article]] = []
    undated: list[Article] = []
    for article in articles:
        article_time = article.published or article.collected_at
        event_at = _as_utc(article_time) if article_time else None
        if event_at:
            dated.append((event_at, article))
        else:
            undated.append(article)
    if dated:
        return max(dated, key=lambda item: item[0])[1]
    return undated[0] if undated else None


def _event_datetime(article: Article | None, source: Source) -> datetime | None:
    if article is None:
        return None
    field = str(
        source.config.get("observed_date_field")
        or source.config.get("event_date_field")
        or ""
    )
    if field == "collected_at":
        return _as_utc(article.collected_at) if article.collected_at else None
    article_time = article.published or article.collected_at
    return _as_utc(article_time) if article_time else None


def _refund_event_datetime(
    article: Article | None,
    source: Source,
    event_model: str,
) -> datetime | None:
    if article is None:
        return None
    if event_model == "refund_claim_window":
        deadline = _parse_datetime(_first(article.matched_entities, "ClaimDeadline"))
        if deadline is not None:
            return deadline
    if event_model == "complaint_resolution":
        resolution_date = _parse_datetime(
            _first(article.matched_entities, "ResolutionDate")
        )
        if resolution_date is not None:
            return resolution_date
    if event_model == "refund_policy_change":
        effective_date = _parse_datetime(
            _first(article.matched_entities, "PolicyEffectiveDate")
            or _first(article.matched_entities, "EffectiveDate")
        )
        if effective_date is not None:
            return effective_date
    return _event_datetime(article, source)


def _event_status(
    *,
    event_at: datetime | None,
    age_days: float | None,
    sla_days: int | None,
) -> str:
    if event_at is None or age_days is None:
        return "unknown_event_date"
    if sla_days is not None and age_days > sla_days:
        return "stale"
    return "fresh"


def _refund_event_key(*, article: Article, source: Source, event_model: str) -> str:
    if event_model == "refund_claim_window":
        date_part = _first(article.matched_entities, "ClaimDeadline")
    elif event_model == "complaint_resolution":
        date_part = _first(article.matched_entities, "ResolutionDate")
    elif event_model == "refund_policy_change":
        date_part = _first(article.matched_entities, "PolicyEffectiveDate") or _first(
            article.matched_entities,
            "EffectiveDate",
        )
    else:
        date_part = article.published.date().isoformat() if article.published else ""
    key_parts = [
        event_model,
        source.country,
        source.name,
        date_part,
        ",".join(_list(article.matched_entities.get("ResolutionStatus"))),
        article.title or article.link,
    ]
    return ":".join(_normalize_key_text(part) for part in key_parts if str(part).strip())


def _source_errors(source_name: str, errors: list[str]) -> list[str]:
    colon_prefix = f"{source_name}:"
    bracket_prefix = f"[{source_name}]"
    return [
        error
        for error in errors
        if error.startswith(colon_prefix) or error.startswith(bracket_prefix)
    ]


def _first(mapping: Mapping[str, list[str]], key: str) -> str:
    values = _list(mapping.get(key))
    return values[0] if values else ""


def _list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_set(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, tuple | set):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, str) and value.strip():
        return {value.strip()}
    return set()


def _normalize_key_text(value: object) -> str:
    text = str(value).strip().lower()
    normalized = "".join(char if char.isalnum() else "-" for char in text)
    return "-".join(part for part in normalized.split("-") if part)


def _age_days(generated_at: datetime, event_at: datetime) -> float:
    return max(0.0, (_as_utc(generated_at) - _as_utc(event_at)).total_seconds() / 86400)


def _dict(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None
