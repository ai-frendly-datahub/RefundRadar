from __future__ import annotations

from refundradar.config_loader import load_category_config, load_category_quality_config


def test_real_refund_config_exposes_data_quality_overlay() -> None:
    metadata = load_category_quality_config("refund")

    data_quality = metadata["data_quality"]
    assert isinstance(data_quality, dict)
    assert data_quality["priority"] == "P0"
    assert data_quality["primary_motion"] == "compliance-risk"
    assert "refund_claim_window" in data_quality["event_models"]
    assert "complaint_resolution" in data_quality["event_models"]
    assert "recall_refund_notice" in data_quality["event_models"]
    assert data_quality["canonical_keys"]["refund_case"]["fields"]
    quality_outputs = data_quality["quality_outputs"]
    assert quality_outputs["freshness_report"] == "reports/refund_quality.json"
    assert quality_outputs["dated_freshness_report_pattern"] == (
        "reports/refund_YYYYMMDD_quality.json"
    )
    assert set(quality_outputs["tracked_event_models"]) >= {
        "refund_claim_window",
        "complaint_resolution",
        "recall_refund_notice",
        "refund_policy_change",
    }

    backlog = metadata["source_backlog"]
    assert isinstance(backlog, dict)
    policy_candidates = {candidate["id"] for candidate in backlog["policy_diff_candidates"]}
    resolution_candidates = {
        candidate["id"] for candidate in backlog["complaint_resolution_candidates"]
    }
    assert policy_candidates >= {
        "us_dot_airline_customer_service_dashboard",
        "merchant_refund_policy_pages",
    }
    assert resolution_candidates >= {
        "cfpb_consumer_complaint_database",
        "consumer24_damage_relief",
    }
    community_candidates = {
        candidate["id"] for candidate in backlog["community_complaint_candidates"]
    }
    assert "reddit_refund_complaint_threads" in community_candidates


def test_real_refund_sources_preserve_operational_metadata() -> None:
    config = load_category_config("refund")
    sources = {source.name: source for source in config.sources}

    irs = sources["IRS Newsroom"]
    assert irs.trust_tier == "T1_official"
    assert "refund_claim_window" in irs.info_purpose
    assert irs.config["event_model"] == "refund_claim_window"
    assert irs.config["observed_date_field"] == "collected_at"
    assert irs.config["canonical_key_fields"]

    cfpb_blog = sources["CFPB Blog"]
    assert cfpb_blog.config["event_model"] == "regulatory_guidance"
    assert "regulatory_guidance" in cfpb_blog.info_purpose

    cfpb = sources["CFPB Newsroom"]
    assert cfpb.config["event_model"] == "regulatory_guidance"
    assert "regulatory_guidance" in cfpb.info_purpose

    cpsc = sources["CPSC Recalls"]
    assert cpsc.config["event_model"] == "recall_refund_notice"
    assert "refund_action" in cpsc.info_purpose

    kca = sources["한국소비자원"]
    assert kca.config["event_model"] == "complaint_resolution"
    assert kca.config["freshness_sla_days"] == 2


def test_real_refund_reddit_sources_remain_disabled_until_adapter_exists() -> None:
    config = load_category_config("refund")
    reddit_sources = [source for source in config.sources if source.type.lower() == "reddit"]

    assert {source.name for source in reddit_sources} >= {
        "Reddit r/tax",
        "Reddit r/personalfinance",
        "Reddit r/legaladvice",
        "Reddit r/consumerrights",
    }
    assert all(not source.enabled for source in reddit_sources)
    assert all(source.config["event_model"] == "complaint_signal" for source in reddit_sources)
    assert all(source.config["merge_policy"] == "cross_reference_only" for source in reddit_sources)
    assert all(
        source.config["disabled_reason"] == "unsupported_reddit_collector"
        for source in reddit_sources
    )
