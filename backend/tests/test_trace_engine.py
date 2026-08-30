from backend.graph.trace_engine import bounded_trace, build_transaction_graph


def test_bounded_trace_stops_at_max_hops():
    txs = [
        {"from": "0xaaa", "to": "0xbbb", "amount": 5.0, "tx_hash": "t1"},
        {"from": "0xbbb", "to": "0xccc", "amount": 7.0, "tx_hash": "t2"},
        {"from": "0xccc", "to": "0xddd", "amount": 9.0, "tx_hash": "t3"},
    ]
    graph = build_transaction_graph(txs)
    nodes, edges = bounded_trace(graph, ["0xaaa"], max_hops=2)
    assert "0xaaa" in nodes
    assert "0xccc" in nodes
    assert "0xddd" not in nodes
    assert len(edges) <= 3
