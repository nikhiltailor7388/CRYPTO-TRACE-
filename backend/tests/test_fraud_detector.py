from backend.services.fraud_detector import build_graph_hash, calculate_multilayer_probability


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
