from backend.services.attribution import apply_fifo_attribution


def test_no_outflow():
    # suspect receives funds but never sends out
    txs = [
        {"tx_hash":"t1","from":"0xvictim","to":"0xaaa","amount":10.0,"timestamp":"2024-06-01T09:00:00Z"}
    ]
    evidence, annotated = apply_fifo_attribution(txs, ["0xaaa"])
    # No outgoing tx => traceable amounts for outflows are zero (no outflow present)
    assert len(evidence) == 1
    assert evidence[0]["traceable_amount"] == 0.0


def test_cycle_attribution():
    # A->B, B->A cycle where suspect is A
    txs = [
        {"tx_hash":"t1","from":"0xvictim","to":"0xa","amount":10.0,"timestamp":"2024-06-01T09:00:00Z"},
        {"tx_hash":"t2","from":"0xa","to":"0xb","amount":5.0,"timestamp":"2024-06-01T10:00:00Z"},
        {"tx_hash":"t3","from":"0xb","to":"0xa","amount":2.0,"timestamp":"2024-06-01T11:00:00Z"}
    ]
    evidence, annotated = apply_fifo_attribution(txs, ["0xa"])  # A is suspect
    # t2 traceable should be min(A_suspected=10, 5) = 5
    t2 = next(e for e in evidence if e["tx_hash"]=="t2")
    assert t2["traceable_amount"] == 5.0
    # t3: B->A, B had suspected_balance after t2 of 5 => t3 traceable = min(5,2)=2
    t3 = next(e for e in evidence if e["tx_hash"]=="t3")
    assert t3["traceable_amount"] == 2.0


def test_multiple_incoming_sources():
    # A receives suspected 10, B sends 5 (non-suspect), then A sends out 12
    txs = [
        {"tx_hash":"t1","from":"0xvictim","to":"0xa","amount":10.0,"timestamp":"2024-06-01T09:00:00Z"},
        {"tx_hash":"t2","from":"0xb","to":"0xa","amount":5.0,"timestamp":"2024-06-01T09:30:00Z"},
        {"tx_hash":"t3","from":"0xa","to":"0xc","amount":12.0,"timestamp":"2024-06-01T10:00:00Z"}
    ]
    evidence, annotated = apply_fifo_attribution(txs, ["0xa"])  # A is suspect
    t3 = next(e for e in evidence if e["tx_hash"]=="t3")
    # suspected balance for A before t3 is 10 (from victim). So traceable = min(10,12)=10
    assert t3["traceable_amount"] == 10.0
    assert t3["unclassified_amount"] == 2.0


def test_token_transfer_handling():
    # token txs should be handled: value scaled via normalizer in main flow; attribution expects amounts numeric
    txs = [
        {"tx_hash":"t1","from":"0xvictim","to":"0xa","amount":100.0,"timestamp":"2024-06-01T09:00:00Z","asset":"TOKEN"},
        {"tx_hash":"t2","from":"0xa","to":"0xb","amount":50.0,"timestamp":"2024-06-01T10:00:00Z","asset":"TOKEN"}
    ]
    evidence, annotated = apply_fifo_attribution(txs, ["0xa"])  # A suspect
    t2 = next(e for e in evidence if e["tx_hash"]=="t2")
    assert t2["traceable_amount"] == 50.0
    assert t2["unclassified_amount"] == 0.0
