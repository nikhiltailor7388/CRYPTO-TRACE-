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


def test_trace_requires_supplied_transaction_id_to_exist(monkeypatch):
    from fastapi import HTTPException
    from types import SimpleNamespace
    from backend.api.trace_impl import TraceRequest, trace

    monkeypatch.setattr(
        "backend.api.trace_impl.fetch_transactions",
        lambda *args, **kwargs: [
            {
                "tx_hash": "0xknown",
                "from": "0x1111111111111111111111111111111111111111",
                "to": "0x2222222222222222222222222222222222222222",
                "amount": 1.0,
                "asset": "ETH",
                "timestamp": "2024-01-01T00:00:00Z",
                "block": 1,
            }
        ],
    )
    request = TraceRequest(
        case_id="TEST-MISSING-TX",
        wallets=["0x1111111111111111111111111111111111111111"],
        tx_hash="0xmissing",
    )
    try:
        trace(request, SimpleNamespace(headers={}))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected a missing transaction ID to return 404")


def test_multi_hop_trace_fetches_downstream_wallet_history(monkeypatch):
    from types import SimpleNamespace
    from backend.api.trace_impl import TraceRequest, trace

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"
    wallet_c = "0x3333333333333333333333333333333333333333"
    histories = {
        wallet_a: [{"tx_hash": "t1", "from": wallet_a, "to": wallet_b, "amount": 2.0, "asset": "ETH", "timestamp": "2024-01-01T00:00:00Z", "block": 1}],
        wallet_b: [{"tx_hash": "t2", "from": wallet_b, "to": wallet_c, "amount": 1.0, "asset": "ETH", "timestamp": "2024-01-01T01:00:00Z", "block": 2}],
    }
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr("backend.api.trace_impl.fetch_transactions", lambda address, **kwargs: histories.get(address, []))
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace(TraceRequest(case_id="MULTI-HOP", wallets=[wallet_a], max_hops=2), SimpleNamespace(headers={}))
    assert {item["tx_hash"] for item in response["evidence"]} == {"t1", "t2"}
    assert len(response["graph"]["edges"]) == 2
    nodes_by_id = {node["id"]: node for node in response["graph"]["nodes"]}
    assert nodes_by_id[wallet_a]["hop_depth"] == 0
    assert nodes_by_id[wallet_b]["hop_depth"] == 1
    assert nodes_by_id[wallet_c]["hop_depth"] == 2
    assert {edge["hop"] for edge in response["graph"]["edges"]} == {1, 2}


def test_parallel_transactions_are_not_dropped_from_graph():
    from backend.services.graph_utils import bfs_subgraph_from_graph, build_graph_from_txs

    txs = [
        {"tx_hash": "t1", "from": "0xa", "to": "0xb", "amount": 1, "timestamp": "2024-01-01T00:00:00Z"},
        {"tx_hash": "t2", "from": "0xa", "to": "0xb", "amount": 2, "timestamp": "2024-01-01T00:01:00Z"},
    ]
    _, edges = bfs_subgraph_from_graph(build_graph_from_txs(txs), ["0xa"], max_hops=1)
    assert {edge[2] for edge in edges} == {"t1", "t2"}


def test_tron_requires_its_own_provider_configuration(monkeypatch):
    from fastapi import HTTPException
    from types import SimpleNamespace
    from backend.api import trace_impl

    monkeypatch.delenv("TRONSCAN_API_KEY", raising=False)
    monkeypatch.setattr(trace_impl, "settings", SimpleNamespace(
        use_etherscan=True, demo_mode=False, etherscan_api_key="test", tronscan_api_key="",
    ))
    try:
        trace_impl.trace(trace_impl.TraceRequest(chain="TRON", wallets=["TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV"]), SimpleNamespace(headers={}))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "TRONSCAN_API_KEY" in exc.detail
    else:
        raise AssertionError("Expected missing TronScan configuration to be visible")


def test_trace_excludes_inbound_history_from_outbound_evidence(monkeypatch):
    from types import SimpleNamespace
    from backend.api import trace_impl

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"
    unrelated = "0x3333333333333333333333333333333333333333"
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(trace_impl, "fetch_transactions", lambda address, **kwargs: [
        {"tx_hash": "inbound", "from": unrelated, "to": wallet_a, "amount": 7, "timestamp": "2024-01-01T00:00:00Z"},
        {"tx_hash": "outbound", "from": wallet_a, "to": wallet_b, "amount": 2, "timestamp": "2024-01-01T01:00:00Z"},
    ] if address == wallet_a else [])
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace_impl.trace(trace_impl.TraceRequest(case_id="OUTBOUND", wallets=[wallet_a], max_hops=1), SimpleNamespace(headers={}))
    assert [item["tx_hash"] for item in response["evidence"]] == ["outbound"]


def test_omitted_case_id_keeps_wallet_traces_isolated(monkeypatch):
    """The UI omits a case ID for a new investigation; each result must be distinct."""
    from types import SimpleNamespace
    from backend.api import trace_impl

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"
    histories = {
        wallet_a: [{"tx_hash": "wallet-a", "from": wallet_a, "to": "0x3333333333333333333333333333333333333333", "amount": 1, "timestamp": "2024-01-01T00:00:00Z"}],
        wallet_b: [{"tx_hash": "wallet-b", "from": wallet_b, "to": "0x4444444444444444444444444444444444444444", "amount": 2, "timestamp": "2024-01-02T00:00:00Z"}],
    }
    saved = {}
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(trace_impl, "fetch_transactions", lambda address, **kwargs: histories.get(address, []))
    monkeypatch.setattr("backend.services.persistence.save_case", lambda case_id, payload, **kwargs: saved.setdefault(case_id, payload))

    result_a = trace_impl.trace(trace_impl.TraceRequest(wallets=[wallet_a], max_hops=1), SimpleNamespace(headers={}))
    result_b = trace_impl.trace(trace_impl.TraceRequest(wallets=[wallet_b], max_hops=1), SimpleNamespace(headers={}))

    assert result_a["case_id"] != result_b["case_id"]
    assert result_a["evidence"][0]["tx_hash"] == "wallet-a"
    assert result_b["evidence"][0]["tx_hash"] == "wallet-b"
    assert set(saved) == {result_a["case_id"], result_b["case_id"]}


def test_tron_trace_uses_same_transaction_id_for_evidence_and_graph(monkeypatch):
    from types import SimpleNamespace
    from backend.api import trace_impl

    source = "TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV"
    destination = "TVjsyZ7fYF3qLF6BQgPmTEZy1xrNL6wyKz"
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("TRONSCAN_API_KEY", "test")
    monkeypatch.setattr(trace_impl, "fetch_transactions", lambda address, **kwargs: [{
        "chain": "TRON", "tx_hash": "tron-identity", "from": source, "to": destination,
        "asset": "TRX", "amount": 1.25, "timestamp": "2024-01-01T00:00:00Z",
        "source_url": "https://tronscan.org/#/transaction/tron-identity",
    }])
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace_impl.trace(trace_impl.TraceRequest(case_id="TRON-IDENTITY", chain="TRON", wallets=[source], max_hops=1), SimpleNamespace(headers={}))
    assert response["provider"] == "TronScan"
    assert response["data_source"] == "live"
    assert response["evidence"][0]["tx_hash"] == response["graph"]["edges"][0]["tx_hash"] == "tron-identity"


def test_trace_marks_result_partial_at_wallet_limit(monkeypatch):
    from types import SimpleNamespace
    from backend.api import trace_impl

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"
    wallet_c = "0x3333333333333333333333333333333333333333"
    histories = {
        wallet_a: [
            {"tx_hash": "t1", "from": wallet_a, "to": wallet_b, "amount": 2.0, "timestamp": None},
            {"tx_hash": "t2", "from": wallet_a, "to": wallet_c, "amount": 1.0, "timestamp": None},
        ],
        wallet_b: [{"tx_hash": "t3", "from": wallet_b, "to": wallet_c, "amount": 1.0, "timestamp": None}],
    }
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(trace_impl, "settings", SimpleNamespace(
        use_etherscan=True, demo_mode=False, etherscan_api_key="test", max_trace_wallets=2,
        max_trace_transactions=100, trace_timeout_seconds=60, max_historical_price_lookups=0,
    ))
    monkeypatch.setattr(trace_impl, "fetch_transactions", lambda address, **kwargs: histories.get(address, []))
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace_impl.trace(trace_impl.TraceRequest(case_id="LIMIT", wallets=[wallet_a], max_hops=3), SimpleNamespace(headers={}))
    assert response["status"] == "partial"
    assert response["summary"]["partial"] is True
    assert response["summary"]["partial_reasons"] == ["wallet_limit_reached"]
    assert len(response["evidence"]) == len(response["graph"]["edges"])


def test_cross_chain_boundary_does_not_enqueue_same_chain_continuation(monkeypatch):
    from types import SimpleNamespace
    from backend.api import trace_impl

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"
    calls = []
    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(trace_impl, "settings", SimpleNamespace(
        use_etherscan=True, demo_mode=False, etherscan_api_key="test", max_trace_wallets=10,
        max_trace_transactions=100, trace_timeout_seconds=60, max_historical_price_lookups=0,
    ))
    monkeypatch.setattr(trace_impl, "fetch_transactions", lambda address, **kwargs: calls.append(address) or [{
        "tx_hash": "bridge", "from": wallet_a, "to": wallet_b, "amount": 1.0, "timestamp": None,
        "chain": "ETH", "source_chain": "ETH", "destination_chain": "BSC",
    }])
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace_impl.trace(trace_impl.TraceRequest(case_id="BRIDGE", wallets=[wallet_a], max_hops=3), SimpleNamespace(headers={}))
    assert calls == [wallet_a]
    assert response["cross_chain_boundaries"][0]["continuation_status"] == "unsupported_cross_chain"
