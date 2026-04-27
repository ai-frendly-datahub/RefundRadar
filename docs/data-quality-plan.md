# Data Quality Plan

- 생성 시각: `2026-04-11T16:05:37.910248+00:00`
- 우선순위: `P0`
- 데이터 품질 점수: `96`
- 가장 약한 축: `추적성`
- Governance: `high`
- Primary Motion: `compliance-risk`

## 현재 이슈

- 현재 설정상 즉시 차단 이슈 없음. 운영 지표와 freshness SLA만 명시하면 됨

## 필수 신호

- 환불·리콜·소비자 구제 공식 공지
- 판매자·항공사·플랫폼별 환불 정책 변경
- 처리 상태와 complaint resolution 결과

## 품질 게이트

- 환불 가능 조건과 실제 처리 상태를 분리
- 정책 변경일과 적용 시작일을 별도 필드로 유지
- 커뮤니티 불만은 공식 구제 결과와 cross-reference로만 사용

## 다음 구현 순서

- refund_claim_window와 complaint_resolution freshness/stale 리포트를 검증 산출물에 추가
- seller/airline policy diff와 complaint resolution 후보는 source_backlog에서 ToS·개인정보·parser 검증 후 단계적 활성화
- 환불 사건별 claim deadline·resolution status·근거 URL을 결과 리포트에 함께 표시

## 운영 규칙

- 원문 URL, 수집일, 이벤트 발생일은 별도 필드로 유지한다.
- 공식 source와 커뮤니티/시장 source를 같은 신뢰 등급으로 병합하지 않는다.
- collector가 인증키나 네트워크 제한으로 skip되면 실패를 숨기지 말고 skip 사유를 기록한다.
- 이 문서는 `scripts/build_data_quality_review.py --write-repo-plans`로 재생성한다.
