from __future__ import annotations

from collections.abc import Iterable

from .models import Article, Source


TRACKED_EVENT_MODELS = {
    "complaint_resolution",
    "recall_refund_notice",
    "refund_claim_window",
    "refund_policy_change",
}
SOURCE_CONTEXT_PURPOSES = {
    "claim_deadline",
    "complaint_resolution",
    "consumer_protection",
    "refund_action",
    "refund_claim_window",
    "refund_policy_change",
    "tax_refund",
    "recall_refund_notice",
}
OPERATIONAL_ENTITY_NAMES = {
    "ClaimDeadline",
    "ClaimStartDate",
    "OperationalEvent",
    "ResolutionStatus",
}
REFUND_DOMAIN_ENTITY_NAMES = {
    "ConsumerProtection",
    "Eligibility",
    "EnergyRebate",
    "RefundType",
    "Subsidy",
    "TaxBenefit",
}
CORE_REFUND_TERMS = {
    "cashback",
    "chargeback",
    "claim deadline",
    "compensation",
    "refund",
    "refunded",
    "refunds",
    "reimbursement",
    "rebate",
    "settlement",
    "tax credit",
    "tax deduction",
    "tax refund",
    "감면",
    "교환",
    "근로장려금",
    "리콜",
    "반품",
    "보상",
    "세액공제",
    "소득공제",
    "연말정산",
    "자녀장려금",
    "집단소송",
    "청구",
    "캐시백",
    "환급",
    "환급액",
    "환불",
    "회수",
}
CLAIM_TERMS = {
    "apply",
    "claim",
    "claiming",
    "deadline",
    "file",
    "submit",
    "until",
    "기한",
    "마감",
    "신고",
    "신청",
    "접수",
}
RECALL_TERMS = {
    "recall",
    "recalls",
    "recalled",
    "리콜",
    "시정조치",
    "회수",
}
COMPLAINT_TERMS = {
    "complaint",
    "consumer protection",
    "dispute",
    "enforcement",
    "lawsuit",
    "resolution",
    "settlement",
    "공정거래",
    "민원",
    "분쟁",
    "소비자",
    "시정명령",
    "집단소송",
}
STRONG_COMPLAINT_TERMS = {
    "class action",
    "complaint",
    "consumer complaint",
    "consumer dispute",
    "consumer protection",
    "consumer rights",
    "dispute",
    "enforcement",
    "lawsuit",
    "misleading",
    "penalties",
    "penalty",
    "recall",
    "sale prices",
    "settlement",
    "분쟁",
    "분쟁조정",
    "민원",
    "불만",
    "사기",
    "소비자분쟁",
    "소비자보호",
    "시정명령",
    "집단분쟁",
    "집단소송",
    "피해구제",
}
TAX_REFUND_TERMS = {
    "1040",
    "1099",
    "child tax credit",
    "earned income",
    "eitc",
    "filing",
    "irs",
    "tax break",
    "tax credit",
    "tax deduction",
    "tax filing",
    "tax refund",
    "tax return",
    "국세청",
    "근로장려금",
    "세액공제",
    "소득공제",
    "연말정산",
    "자녀장려금",
    "환급액",
}
TAX_TITLE_TERMS = {
    "1040",
    "child tax credit",
    "claim",
    "credit",
    "credits",
    "deadline",
    "deadlines",
    "deduct",
    "deducted",
    "deduction",
    "deductions",
    "eitc",
    "extension",
    "file",
    "filing",
    "refund",
    "refunds",
    "relief",
    "tax break",
    "tax breaks",
    "tax credit",
    "tax credits",
    "tax deduction",
    "tax deductions",
    "tax refund",
    "tax refunds",
    "tax return",
    "tax returns",
    "withholding",
    "공제",
    "국세청",
    "근로장려금",
    "기한",
    "마감",
    "세액공제",
    "소득공제",
    "세금 신고",
    "세무 신고",
    "연말정산",
    "자녀장려금",
    "환급",
    "환급액",
}
REFUND_TITLE_TERMS = CORE_REFUND_TERMS | TAX_TITLE_TERMS | STRONG_COMPLAINT_TERMS | RECALL_TERMS
GENERIC_REFUND_TYPE_VALUES = {
    "claim",
    "credit",
    "get back",
    "getting",
    "payment",
    "receive",
    "return",
    "지급",
}


def apply_source_context_entities(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    classified: list[Article] = []
    for article in articles:
        if article.category != "refund":
            classified.append(article)
            continue

        source = source_map.get(article.source)
        if source is None:
            continue

        tags = _source_context_tags(source)
        if tags:
            existing = article.matched_entities.get("SourceSignal", [])
            existing_values = existing if isinstance(existing, list) else [existing]
            article.matched_entities["SourceSignal"] = sorted(
                {str(value) for value in existing_values} | set(tags)
            )
        classified.append(article)
    return classified


def filter_relevant_articles(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    filtered: list[Article] = []
    for article in articles:
        if article.category != "refund":
            filtered.append(article)
            continue

        source = source_map.get(article.source)
        if source is None:
            continue
        if _is_invalid_page(article):
            continue
        if _has_refund_signal(article, source):
            filtered.append(article)
    return filtered


def _has_refund_signal(article: Article, source: Source) -> bool:
    entity_names = set(article.matched_entities)
    text = f"{article.title} {article.summary}".lower()
    title = article.title.lower()
    source_event_model = _source_event_model(source)
    domain_entities = entity_names & REFUND_DOMAIN_ENTITY_NAMES
    has_core_refund_text = _contains_any(text, CORE_REFUND_TERMS)
    has_core_refund_title = _contains_any(title, REFUND_TITLE_TERMS)

    if source_event_model == "recall_refund_notice":
        return _contains_any(title, RECALL_TERMS) or has_core_refund_title
    if source_event_model == "complaint_resolution":
        return (
            "ConsumerProtection" in entity_names
            and _contains_any(text, STRONG_COMPLAINT_TERMS | CORE_REFUND_TERMS)
        ) or (
            _is_official_operational_source(source)
            and _contains_any(title, STRONG_COMPLAINT_TERMS | CORE_REFUND_TERMS)
        )
    if source_event_model == "refund_claim_window":
        return _has_claim_window_signal(article, text, title, has_core_refund_text) or (
            _is_official_operational_source(source)
            and _contains_any(title, TAX_TITLE_TERMS | CLAIM_TERMS)
        )
    if source_event_model == "refund_policy_change":
        return has_core_refund_title or (
            "TaxBenefit" in entity_names
            and (_contains_any(title, TAX_TITLE_TERMS) or _contains_any(text, CORE_REFUND_TERMS))
        )

    if not domain_entities:
        return False
    if _is_broad_source(source):
        return _has_broad_refund_signal(article, title, has_core_refund_text)
    return has_core_refund_title or bool(entity_names & OPERATIONAL_ENTITY_NAMES)


def _has_claim_window_signal(
    article: Article,
    text: str,
    title: str,
    has_core_refund_text: bool,
) -> bool:
    entity_names = set(article.matched_entities)
    if "ClaimDeadline" in entity_names and (
        has_core_refund_text or _contains_any(title, CLAIM_TERMS | TAX_TITLE_TERMS)
    ):
        return True
    if _contains_any(title, REFUND_TITLE_TERMS) and {"RefundType", "TaxBenefit", "Eligibility"} & entity_names:
        return True
    return "TaxBenefit" in entity_names and _contains_any(title, TAX_TITLE_TERMS)


def _has_broad_refund_signal(
    article: Article,
    title: str,
    has_core_refund_text: bool,
) -> bool:
    entity_names = set(article.matched_entities)
    has_title_refund_signal = _contains_any(title, REFUND_TITLE_TERMS)
    if has_title_refund_signal and has_core_refund_text and not _refund_type_values_are_generic_only(article):
        return True
    if "ConsumerProtection" in entity_names and _contains_any(title, STRONG_COMPLAINT_TERMS | RECALL_TERMS):
        return True
    if "TaxBenefit" in entity_names and _contains_any(title, TAX_TITLE_TERMS):
        return True
    if "EnergyRebate" in entity_names and _contains_any(title, {"credit", "rebate", "tax credit"}):
        return True
    return False


def _source_context_tags(source: Source) -> list[str]:
    tags = {purpose for purpose in source.info_purpose if purpose in SOURCE_CONTEXT_PURPOSES}
    event_model = _source_event_model(source)
    if event_model in TRACKED_EVENT_MODELS:
        tags.add(event_model)
    return sorted(tags)


def _source_event_model(source: Source) -> str:
    raw = source.config.get("event_model")
    return str(raw).strip() if raw is not None else ""


def _is_broad_source(source: Source) -> bool:
    return not _source_event_model(source) and not str(source.trust_tier).startswith("T1_")


def _is_official_operational_source(source: Source) -> bool:
    return str(source.trust_tier).startswith("T1_") and bool(_source_event_model(source))


def _refund_type_values_are_generic_only(article: Article) -> bool:
    values = article.matched_entities.get("RefundType", [])
    if not isinstance(values, list):
        return False
    normalized = {str(value).strip().lower() for value in values if str(value).strip()}
    return bool(normalized) and normalized <= GENERIC_REFUND_TYPE_VALUES


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _is_invalid_page(article: Article) -> bool:
    title = article.title.strip().lower()
    haystack = f"{article.title} {article.summary}".lower()
    normalized_title = " ".join(title.split())
    known_index_titles = {
        "newsroom | internal revenue service",
        "wetax (위택스)",
        "wetax 위택스",
        "보도자료 - 공정거래위원회",
        "한국소비자원",
    }
    if normalized_title in known_index_titles or normalized_title.startswith("식품의약품안전처>"):
        return True
    if any(
        marker in haystack
        for marker in (
            "404",
            "access denied",
            "not found",
            "page not found",
            "request blocked",
            "service unavailable",
            "페이지를 찾을 수 없습니다",
        )
    ):
        return True
    if "skip to main content" in haystack and "main navigation" in haystack:
        return True
    if "본문 바로가기" in haystack and (
        "주메뉴 바로가기" in haystack
        or "통합검색" in haystack
        or "누리집안내지도" in haystack
        or "사이트맵" in haystack
    ):
        return True
    return False
