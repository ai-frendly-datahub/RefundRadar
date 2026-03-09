from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from refundradar.models import Article, CategoryConfig, EntityDefinition, Source
from refundradar.storage import RadarStorage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> RadarStorage:
    """Create a temporary RadarStorage instance for testing."""
    db_path = tmp_path / "test.duckdb"
    storage = RadarStorage(db_path)
    yield storage
    storage.close()


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles with realistic 환급 domain data."""
    now = datetime.now(timezone.utc)
    return [
        Article(
            title="세금 환급 신청 방법",
            link="https://refund.example.com/tax-2024",
            summary="소득세 환급 신청 절차를 안내합니다.",
            published=now,
            source="refundradar_api",
            category="refund",
            matched_entities={},
        ),
        Article(
            title="부가세 환급 안내",
            link="https://refund.example.com/vat-2024",
            summary="부가세 환급 대상 및 신청 방법입니다.",
            published=now,
            source="refundradar_api",
            category="refund",
            matched_entities={},
        ),
        Article(
            title="보험금 환급 절차",
            link="https://refund.example.com/insurance-2024",
            summary="보험금 환급 신청 절차를 안내합니다.",
            published=now,
            source="refundradar_api",
            category="refund",
            matched_entities={},
        ),
        Article(
            title="관세 환급 정보",
            link="https://refund.example.com/customs-2024",
            summary="수입 관세 환급 대상 및 절차입니다.",
            published=now,
            source="refundradar_api",
            category="refund",
            matched_entities={},
        ),
        Article(
            title="지원금 환급 안내",
            link="https://refund.example.com/subsidy-2024",
            summary="정부 지원금 환급 신청 방법입니다.",
            published=now,
            source="refundradar_api",
            category="refund",
            matched_entities={},
        ),
    ]


@pytest.fixture
def sample_entities() -> list[EntityDefinition]:
    """Create sample entities with 환급 domain keywords."""
    return [
        EntityDefinition(
            name="tax_refund",
            display_name="세금 환급",
            keywords=["세금", "환급", "소득세", "신청"],
        ),
        EntityDefinition(
            name="vat_refund",
            display_name="부가세 환급",
            keywords=["부가세", "VAT", "환급", "신청"],
        ),
        EntityDefinition(
            name="insurance_refund",
            display_name="보험금 환급",
            keywords=["보험", "환급", "보험금", "청구"],
        ),
        EntityDefinition(
            name="customs_refund",
            display_name="관세 환급",
            keywords=["관세", "환급", "수입", "통관"],
        ),
        EntityDefinition(
            name="subsidy_refund",
            display_name="지원금 환급",
            keywords=["지원금", "환급", "정부", "신청"],
        ),
    ]


@pytest.fixture
def sample_config(tmp_path: Path, sample_entities: list[EntityDefinition]) -> CategoryConfig:
    """Create a sample CategoryConfig for testing."""
    sources = [
        Source(
            name="refundradar_api",
            type="api",
            url="https://api.refundradar.example.com",
        ),
    ]
    return CategoryConfig(
        category_name="refund",
        display_name="환급",
        sources=sources,
        entities=sample_entities,
    )
