from backend.services.attribution import apply_fifo_attribution


def test_fifo_worked_example():
    # worked example from build doc
    txs = [
        {"tx_hash":"t1","from":"0xvictim","to":"0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1","amount":10.0,"timestamp":"2024-06-01T09:00:00Z"},
        {"tx_hash":"t2","from":"0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1","to":"0xbbb222bbb222bbb222bbb222bbb222bbb222bbb2","amount":20.0,"timestamp":"2024-06-01T10:00:00Z"},
        {"tx_hash":"t3","from":"0xbbb222bbb222bbb222bbb222bbb222bbb222bbb2","to":"0xccc333ccc333ccc333ccc333ccc333ccc333ccc3","amount":5.0,"timestamp":"2024-06-01T11:00:00Z"}
    ]
    evidence, annotated = apply_fifo_attribution(txs, ["0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1"])  # start suspect is A
    # t2: A->B 20 => traceable 10, unclassified 10
    t2 = next(e for e in evidence if e["tx_hash"] == "t2")
    assert t2["traceable_amount"] == 10.0
    assert t2["unclassified_amount"] == 10.0
    # t3: B->C 5 => should trace 5 (from B's suspected 10)
    t3 = next(e for e in evidence if e["tx_hash"] == "t3")
    assert t3["traceable_amount"] == 5.0
    assert t3["unclassified_amount"] == 0.0
