from backend.services.vasp_matcher import load_vasp_labels, match_vasp_for_address


def test_exact_match_case_insensitive():
    labels = load_vasp_labels()
    candidate = match_vasp_for_address("0XCCC333CCC333CCC333CCC333CCC333CCC333CCC3", labels)
    assert candidate is not None
    assert candidate["entity"] == "Example Exchange"


def test_no_match_returns_none():
    labels = load_vasp_labels()
    assert match_vasp_for_address("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef", labels) is None
