from backend.graph.trace_engine import bounded_trace, build_transaction_graph


def test_bounded_trace_stops_at_max_hops():
    txs = [
        {"from": "0xaaa", "to": "0xbbb", "amount": 5.0, "tx_hash": "t1"},
        {"from": "0xbbb", "to": "0xccc", "amount": 7.0, "tx_hash": "t2"},
        {"from": "0xccc", "to": "0xddd", "amount": 9.0, "tx_hash": "t3"},
    ]
    graph = build_transaction_graph(txs)
    nodes, edges, path = bounded_trace(graph, ["0xaaa"], max_hops=2)
    assert "0xaaa" in nodes
    assert "0xccc" in nodes
    assert "0xddd" not in nodes
    assert len(edges) <= 3
    assert path[0] == "0xaaa"


def test_bounded_trace_follows_largest_edge():
    txs = [
        {"from": "0xaaa", "to": "0xbbb", "amount": 5.0, "tx_hash": "small"},
        {"from": "0xaaa", "to": "0xbbb", "amount": 50.0, "tx_hash": "large"},
        {"from": "0xaaa", "to": "0xccc", "amount": 40.0, "tx_hash": "medium"},
    ]
    graph = build_transaction_graph(txs)
    nodes, edges, path = bounded_trace(graph, ["0xaaa"], max_hops=1)
    assert len(edges) == 1
    assert edges[0][1] == "0xbbb"
    assert edges[0][3] == "large"


def test_bounded_trace_returns_ordered_path():
    txs = [
        {"from": "0xaaa", "to": "0xbbb", "amount": 5.0, "tx_hash": "t1"},
        {"from": "0xbbb", "to": "0xccc", "amount": 7.0, "tx_hash": "t2"},
        {"from": "0xccc", "to": "0xddd", "amount": 9.0, "tx_hash": "t3"},
    ]
    graph = build_transaction_graph(txs)
    nodes, edges, path = bounded_trace(graph, ["0xaaa"], max_hops=3)
    assert path == ["0xaaa", "0xbbb", "0xccc", "0xddd"]
    assert len(edges) == 3


def test_bounded_trace_stops_at_dead_end():
    txs = [
        {"from": "0xaaa", "to": "0xbbb", "amount": 5.0, "tx_hash": "t1"},
    ]
    graph = build_transaction_graph(txs)
    nodes, edges, path = bounded_trace(graph, ["0xaaa"], max_hops=3)
    assert len(edges) == 1
    assert path == ["0xaaa", "0xbbb"]
