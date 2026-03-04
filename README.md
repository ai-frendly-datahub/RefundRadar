# RefundRadar

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

소비자 불만, 환불 정책, 분쟁 해결 절차 관련 뉴스를 자동 수집하고 케이스 검색을 지원하는 레이더 프로젝트입니다.

## 프로젝트 목표

- **소비자 분쟁 동향 추적**: 환불, 반품, 차지백, 민원 관련 뉴스를 일일 자동 수집
- **환불 정책 모니터링**: 주요 플랫폼(Amazon, Apple, 쿠팡 등)의 환불 정책 변경 사항 추적
- **케이스 검색 도구**: MCP `case_finder` 도구로 유사 사례를 자연어로 검색하여 분쟁 해결 참고 자료 제공
- **법적 동향 파악**: 집단소송, 소비자 보호 규제, 합의 사례 등 법적 조치 트렌드 분석
- **AI 소비자 도우미**: MCP 서버를 통해 AI 어시스턴트에서 환불/분쟁 정보를 자연어로 검색

## 주요 기능

1. **RSS 자동 수집**: Consumer Reports, The Verge, Ars Technica 등에서 소비자 이슈 기사 수집
2. **엔티티 매칭**: 환불 유형, 민원/불만, 플랫폼, 법적 조치, 소비자 보호 5개 카테고리
3. **DuckDB 저장**: UPSERT 시맨틱 기반 기사 저장
4. **JSONL 원본 보존**: `data/raw/YYYY-MM-DD/{source}.jsonl`
5. **SQLite FTS5 검색**: 전문검색으로 사례 빠르게 검색
6. **자연어 쿼리**: "최근 1개월 아마존 환불 관련" 같은 자연어 검색
7. **HTML 리포트**: 카테고리별 통계가 포함된 자동 리포트
8. **MCP 서버**: search, recent_updates, sql, top_trends, case_finder

## 빠른 시작

```bash
pip install -r requirements.txt
python main.py --category refund --recent-days 7
```

- 리포트: `reports/refund_report.html`
- DB: `data/radar_data.duckdb`

## 프로젝트 구조

```
RefundRadar/
├── refundradar/
│   ├── collector.py       # RSS 수집
│   ├── analyzer.py        # 엔티티 키워드 매칭
│   ├── storage.py         # DuckDB 스토리지
│   ├── reporter.py        # HTML 리포트
│   ├── raw_logger.py      # JSONL 원본 기록
│   ├── search_index.py    # SQLite FTS5
│   ├── nl_query.py        # 자연어 쿼리 파서
│   └── mcp_server/        # MCP 서버 (5개 도구)
├── config/categories/refund.yaml
├── tests/
├── .github/workflows/
└── main.py
```

## MCP 서버 도구

| 도구 | 설명 |
|------|------|
| `search` | FTS5 기반 자연어 검색 |
| `recent_updates` | 최근 수집 기사 조회 |
| `sql` | 읽기 전용 SQL 쿼리 |
| `top_trends` | 엔티티 언급 빈도 트렌드 |
| `case_finder` | 환불/분쟁 케이스 검색 |

## 테스트

```bash
pytest tests/ -v
```

## CI/CD

- `.github/workflows/radar-crawler.yml`: 매일 00:00 UTC 자동 수집
- GitHub Pages로 리포트 자동 배포
