from __future__ import annotations

from collections.abc import Iterable
from html import escape
from pathlib import Path
from typing import Any, Mapping

from radar_core.ontology import build_summary_ontology_metadata
from radar_core.report_utils import (
    generate_index_html as _core_generate_index_html,
)
from radar_core.report_utils import (
    generate_report as _core_generate_report,
)

from .models import Article, CategoryConfig


def generate_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    output_path: Path,
    stats: dict[str, int],
    errors: list[str] | None = None,
    store=None,
    quality_report: Mapping[str, Any] | None = None,
) -> Path:
    """Generate HTML report (delegates to radar-core)."""
    articles_list = list(articles)
    plugin_charts = []

    # --- Universal plugins (entity heatmap + source reliability) ---
    try:
        from radar_core.plugins.entity_heatmap import get_chart_config as _heatmap_config

        _heatmap = _heatmap_config(articles=articles_list)
        if _heatmap is not None:
            plugin_charts.append(_heatmap)
    except Exception:
        pass
    try:
        from radar_core.plugins.source_reliability import get_chart_config as _reliability_config

        _reliability = _reliability_config(store=store)
        if _reliability is not None:
            plugin_charts.append(_reliability)
    except Exception:
        pass

    result = _core_generate_report(
        category=category,
        articles=articles_list,
        output_path=output_path,
        stats=stats,
        errors=errors,
        plugin_charts=plugin_charts if plugin_charts else None,
        ontology_metadata=build_summary_ontology_metadata(
            "RefundRadar",
            category_name=category.category_name,
            search_from=Path(__file__).resolve(),
        ),
    )
    if quality_report:
        _inject_refund_quality_panel(result, quality_report)
        _inject_latest_dated_report_panel(result, category.category_name, quality_report)
    return result


def generate_index_html(
    report_dir: Path,
    summaries_dir: Path | None = None,
) -> Path:
    """Generate index.html (delegates to radar-core)."""
    radar_name = "Refund Radar"
    return _core_generate_index_html(report_dir, radar_name)


def _inject_latest_dated_report_panel(
    output_path: Path,
    category_name: str,
    quality_report: Mapping[str, Any],
) -> None:
    dated_reports = sorted(
        output_path.parent.glob(
            f"{category_name}_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].html"
        ),
        key=lambda path: path.stat().st_mtime,
    )
    if dated_reports:
        _inject_refund_quality_panel(dated_reports[-1], quality_report)


def _inject_refund_quality_panel(
    output_path: Path,
    quality_report: Mapping[str, Any],
) -> None:
    if not output_path.exists():
        return
    html = output_path.read_text(encoding="utf-8")
    if 'id="refund-quality"' in html:
        return

    marker = '<section id="entities"'
    if marker not in html:
        return

    panel = _render_refund_quality_panel(quality_report)
    output_path.write_text(
        html.replace(marker, panel.strip("\n") + "\n      " + marker, 1),
        encoding="utf-8",
    )


def _render_refund_quality_panel(quality_report: Mapping[str, Any]) -> str:
    summary = quality_report.get("summary")
    summary_map = summary if isinstance(summary, Mapping) else {}
    sources = [row for row in _list(quality_report.get("sources")) if isinstance(row, Mapping)]
    events = [row for row in _list(quality_report.get("events")) if isinstance(row, Mapping)]
    flagged_sources = [
        row
        for row in sources
        if str(row.get("status")) in {"stale", "missing", "unknown_event_date"}
    ][:6]
    highlighted_events = events[:6]
    chips = [
        ("fresh", summary_map.get("fresh_sources", 0)),
        ("stale", summary_map.get("stale_sources", 0)),
        ("missing", summary_map.get("missing_sources", 0)),
        ("claim windows", summary_map.get("refund_claim_window_events", 0)),
        ("recall notices", summary_map.get("recall_refund_notice_events", 0)),
        ("resolutions", summary_map.get("complaint_resolution_events", 0)),
        ("policy changes", summary_map.get("refund_policy_change_events", 0)),
    ]
    chip_html = "\n".join(
        f'<span class="chip"><strong>{escape(label)}</strong> {escape(str(value))}</span>'
        for label, value in chips
    )
    note = escape(str(quality_report.get("community_complaint_note") or ""))
    return f"""
      <section id="refund-quality" class="section" aria-label="Refund quality">
        <div class="section-hd">
          <h2>Refund Quality</h2>
          <div class="right">
            <span class="kbd">refund_quality.json</span>
          </div>
        </div>
        <article class="panel">
          <header class="panel-hd">
            <div>
              <p class="panel-title">Claim and Resolution Checks</p>
              <p class="panel-sub">freshness, claim windows, recall notices, and official resolutions</p>
            </div>
          </header>
          <div class="panel-bd">
            <div class="row" aria-label="Refund quality summary">
              {chip_html}
            </div>
            <p class="muted small">{note}</p>
            {_render_quality_sources(flagged_sources)}
            {_render_refund_events(highlighted_events)}
          </div>
        </article>
      </section>
"""


def _render_quality_sources(flagged_sources: list[Mapping[str, Any]]) -> str:
    if not flagged_sources:
        return '<p class="muted small">No stale or missing tracked sources in this run.</p>'

    items: list[str] = []
    for row in flagged_sources:
        source = escape(str(row.get("source", "")))
        status = escape(str(row.get("status", "")))
        model = escape(str(row.get("event_model", "")))
        age = row.get("age_days")
        age_text = "" if age is None else f", age {escape(str(age))}d"
        items.append(f"<li><strong>{source}</strong>: {status} ({model}{age_text})</li>")
    return "<ul>" + "\n".join(items) + "</ul>"


def _render_refund_events(events: list[Mapping[str, Any]]) -> str:
    if not events:
        return '<p class="muted small">No tracked refund events in this run.</p>'

    items: list[str] = []
    for event in events:
        title = escape(str(event.get("title", "")))
        model = escape(str(event.get("event_model", "")))
        source = escape(str(event.get("source", "")))
        details = _event_details(event)
        items.append(f"<li><strong>{model}</strong> {title} ({source}){details}</li>")
    return "<ul>" + "\n".join(items) + "</ul>"


def _event_details(event: Mapping[str, Any]) -> str:
    values: list[str] = []
    start_date = str(event.get("claim_start_date") or "")
    deadline = str(event.get("claim_deadline") or "")
    statuses = _list(event.get("resolution_status"))
    if start_date:
        values.append(f"claims open {escape(start_date)}")
    if deadline:
        values.append(f"deadline {escape(deadline)}")
    if statuses:
        values.append("status " + escape(", ".join(str(item) for item in statuses)))
    return "" if not values else ": " + "; ".join(values)


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []
