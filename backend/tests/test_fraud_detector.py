from backend.services.fraud_detector import apply_canonical_risk, build_graph_hash, calculate_multilayer_probability


def test_multilayer_probability_in_expected_range():
    evidence = [
        {"from": "0xvictim", "to": "0xaaa111", "amount": 10.0, "traceable_amount": 0.0, "unclassified_amount": 10.0, "vasp": "UNKNOWN"},
        {"from": "0xaaa111", "to": "0xbbb222", "amount": 20.0, "traceable_amount": 10.0, "unclassified_amount": 10.0, "vasp": "UNKNOWN"},
        {"from": "0xbbb222", "to": "0xccc333", "amount": 5.0, "traceable_amount": 5.0, "unclassified_amount": 0.0, "vasp": "Example Exchange"},
    ]

    result = calculate_multilayer_probability(evidence, ["0xvictim"])
    assert 0 <= result["overall_probability"] <= 99
    assert result["confidence"] in {"low", "medium", "high"}
    assert result["fraudster_candidate"] is not None


def test_graph_hash_is_stable_for_same_case():
    first = build_graph_hash("CASE-001", ["0xvictim"], [{"from": "0xvictim", "to": "0xaaa111", "amount": 10.0, "tx_hash": "t1"}])
    second = build_graph_hash("CASE-001", ["0xvictim"], [{"from": "0xvictim", "to": "0xaaa111", "amount": 10.0, "tx_hash": "t1"}])
    assert first == second


def test_risk_score_is_evidence_based_not_a_default_fifty():
    ordinary = [{"from": "0xvictim", "to": "0xaaa", "amount": 1.0, "traceable_amount": 1.0, "unclassified_amount": 0.0, "vasp": "UNKNOWN"}]
    suspicious = ordinary + [
        {"from": "0xaaa", "to": "0xbbb", "amount": 1.0, "traceable_amount": 0.0, "unclassified_amount": 1.0, "vasp": "Known Exchange"},
        {"from": "0xbbb", "to": "0xccc", "amount": 1.0, "traceable_amount": 0.0, "unclassified_amount": 1.0, "vasp": "UNKNOWN"},
    ]
    low = calculate_multilayer_probability(ordinary, ["0xvictim"])
    high = calculate_multilayer_probability(suspicious, ["0xvictim"])
    assert low["evidence_state"] == "limited"
    assert high["evidence_state"] == "sufficient"
    assert high["risk_score"] > low["risk_score"]
    assert high["risk_score"] != 50


def test_behavioural_risk_patterns_are_deterministic_and_separated_from_vasp_context():
    ordinary = [{"from": "0xa", "to": "0xb", "amount": 1, "timestamp": "2025-01-01T00:00:00Z", "vasp": "Known Exchange"}]
    rapid = ordinary + [{"from": "0xb", "to": "0xc", "amount": 1, "timestamp": "2025-01-01T00:20:00Z"}]
    layering = rapid + [{"from": "0xc", "to": "0xd", "amount": 1, "timestamp": "2025-01-01T03:00:00Z"}]
    mixer = layering + [{"from": "0xd", "to": "0xabc0000000000000000000000000000000000000", "amount": 1, "timestamp": "2025-01-01T03:10:00Z"}]
    ordinary_score = calculate_multilayer_probability(ordinary, ["0xa"])["risk_score"]
    rapid_score = calculate_multilayer_probability(rapid, ["0xa"])["risk_score"]
    layering_score = calculate_multilayer_probability(layering, ["0xa"])["risk_score"]
    mixer_score = calculate_multilayer_probability(mixer, ["0xa"])["risk_score"]
    assert ordinary_score == 0  # VASP attribution alone is not risk.
    assert 0 < rapid_score < mixer_score <= 100
    assert layering_score >= rapid_score
    assert calculate_multilayer_probability(mixer, ["0xa"])["risk_score"] == mixer_score


def test_consolidation_and_splitting_add_risk_only_when_observed():
    consolidation = [
        {"from": f"0x{i}", "to": "0xhub", "amount": 1, "timestamp": "2025-01-01T00:00:00Z"}
        for i in range(3)
    ]
    splitting = [
        {"from": "0xsource", "to": f"0x{i}", "amount": 1, "timestamp": "2025-01-01T00:00:00Z"}
        for i in range(3)
    ]
    assert calculate_multilayer_probability(consolidation, ["0x0"])["risk_score"] >= 5
    assert calculate_multilayer_probability(splitting, ["0xsource"])["risk_score"] >= 5


def test_weak_evidence_does_not_hit_default_high_risk():
    profile = calculate_multilayer_probability([
        {"from": "0xa", "to": "0xb", "amount": 1.0, "timestamp": "2025-01-01T00:00:00Z"}
    ], ["0xa"])
    assert profile["risk_score"] < 20
    assert profile["risk_score"] != 99
    assert profile["trace_confidence"] in {"low", "medium"}


def test_different_evidence_produces_different_scores():
    weak = [{"from": "0xa", "to": "0xb", "amount": 1.0, "timestamp": "2025-01-01T00:00:00Z"}]
    strong = weak + [
        {"from": "0xb", "to": "0xc", "amount": 1.0, "timestamp": "2025-01-01T00:12:00Z"},
        {"from": "0xc", "to": "0xd", "amount": 1.0, "timestamp": "2025-01-01T00:24:00Z"},
    ]
    low_profile = calculate_multilayer_probability(weak, ["0xa"])
    high_profile = calculate_multilayer_probability(strong, ["0xa"])
    assert low_profile["risk_score"] != high_profile["risk_score"]
    assert high_profile["risk_score"] > low_profile["risk_score"]


def test_trace_confidence_is_separate_from_risk_score():
    evidence = [
        {"from": "0xa", "to": "0xb", "amount": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
        {"from": "0xb", "to": "0xc", "amount": 1.0, "timestamp": "2025-01-01T00:10:00Z"},
    ]
    profile = calculate_multilayer_probability(evidence, ["0xa"])
    assert profile["trace_confidence"] in {"medium", "high"}
    assert profile["risk_score"] != profile["trace_confidence"]


def test_legacy_case_conflicting_scores_are_replaced_by_evidence_score():
    case = {
        "chain": "ETH",
        "wallets": [{"address": "0xa"}],
        "summary": {"risk_score": 99, "fraud_probability": 43, "trace_confidence": "unknown"},
        "risk_profile": {"overall_probability": 43, "risk_score": 43, "trace_confidence": "unknown"},
        "evidence": [{"from": "0xa", "to": "0xb", "amount": 1, "timestamp": "2025-01-01T00:00:00Z"}],
    }
    result = apply_canonical_risk(case)
    assert result["summary"]["risk_score"] == 0
    assert result["summary"]["fraud_probability"] == 0
    assert result["summary"]["trace_confidence"] in {"low", "medium"}
    assert result["risk_profile"]["overall_probability"] == 0
    assert result["risk_profile"]["trace_confidence"] == result["summary"]["trace_confidence"]
