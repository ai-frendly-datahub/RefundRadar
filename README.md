# RefundRadar

RefundRadar는 민원/환불 이슈를 추적하는 경량 ETL 프로젝트입니다. RSS 수집, 키워드 기반 엔티티 매칭,
DuckDB 저장, SQLite FTS5 검색 인덱스, HTML 리포트 생성, MCP 도구를 포함합니다.

## Quick Start

```bash
pip install -r requirements.txt
python main.py --category refund --recent-days 7
```

생성 결과:
- 리포트: `reports/refund_report.html`
- 데이터베이스: `data/radar_data.duckdb`
- 검색 인덱스: `data/search_index.db`
- 원본 로그(JSONL): `data/raw/YYYY-MM-DD/*.jsonl`

## Category

- 기본 카테고리: `config/categories/refund.yaml`
- 템플릿: `config/categories/_template.yaml`

## MCP Tools

- `search`
- `recent_updates`
- `sql`
- `top_trends`
- `case_finder`
