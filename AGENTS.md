# REFUNDRADAR

세금 환급, 보험금 환급, 각종 지원금 환급 정보를 수집하고 환급 기한 및 절차를 분석합니다.

## STRUCTURE

```
RefundRadar/
├── refundradar/
│   ├── collector.py              # collect_sources() — 세무청, 보험사 뉴스 및 공고
│   ├── analyzer.py               # apply_entity_rules() — 환급 유형별 키워드 매칭 (세금, 보험, 지원금 등)
│   ├── reporter.py               # generate_report() — Jinja2 HTML
│   ├── storage.py                # RadarStorage — DuckDB upsert/query/retention
│   ├── models.py                 # Source, Article, EntityDefinition, CategoryConfig
│   ├── config_loader.py          # YAML 로딩
│   ├── logger.py                 # structlog 구조화 로깅
│   ├── notifier.py               # Email/Webhook 알림
│   ├── raw_logger.py             # JSONL 원시 로깅
│   ├── search_index.py           # SQLite FTS5 전문 검색
│   ├── nl_query.py               # 자연어 쿼리 파서
│   ├── common/                   # 공유 유틸리티
│   └── mcp_server/               # MCP 서버 (server.py + tools.py)
├── config/
│   ├── config.yaml               # database_path, report_dir, raw_data_dir, search_db_path
│   └── categories/refund.yaml  # 소스 + 엔티티 정의
├── data/                         # DuckDB, search_index.db, raw/ JSONL
├── reports/                      # 생성된 HTML 리포트
├── tests/unit/                   # pytest 단위 테스트
├── main.py                       # CLI 엔트리포인트
└── .github/workflows/radar-crawler.yml
```

## ENTITIES

| Entity | Examples |
|--------|----------|
| RefundType | refund, rebate, reimbursement |
| TaxBenefit | tax credit, tax deduction, 세액공제 |
| Subsidy | subsidy, grant, stimulus, 지원금 |
| ConsumerProtection | recall, settlement, consumer rights |

## DEVIATIONS FROM TEMPLATE

- 환급, 리베이트, 보조금, 리콜/합의금 source를 같은 conversion motion으로 추적한다.
- eligibility와 금액/규모 신호는 요약 문구와 분리해 evidence를 유지한다.
- 세무·소비자 보호 공식 source와 커뮤니티 source의 신뢰 등급을 구분한다.

## COMMANDS

```bash
python main.py --category refund --recent-days 7
python main.py --category refund --per-source-limit 50 --keep-days 90
```
