import json
from pathlib import Path
from types import SimpleNamespace

from backend.graph.trace_engine import bounded_trace, build_transaction_graph
from backend.services.fetcher import fetch_transactions
from backend.services.normalizer import normalize_etherscan_raw, normalize_tron_raw

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_eth_demo_fixture_is_real_and_normalizable():
    with open(DATA_DIR / "eth_cache.json", "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    assert len(rows) >= 3
    assert rows[0]["chain"] == "ETH"
    normalized = normalize_etherscan_raw(rows)
    assert normalized[0]["tx_hash"] == rows[0]["tx_hash"]
    assert normalized[0]["amount"] > 0


def test_tron_demo_fixture_is_real_and_normalizable():
    with open(DATA_DIR / "tron_cache.json", "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    assert len(rows) >= 3
    assert rows[0]["chain"] == "TRON"
    normalized = normalize_tron_raw(rows)
    assert normalized[0]["tx_hash"] == rows[0]["tx_hash"]
    assert normalized[0]["amount"] > 0
    assert normalized[1]["amount"] == rows[1]["amount"]


def test_fetch_transactions_falls_back_to_eth_demo_fixture(monkeypatch):
    monkeypatch.setattr("backend.services.fetcher.settings", SimpleNamespace(etherscan_api_key="", tronscan_api_key="", max_retries=1, backoff_seconds=0))
    rows = fetch_transactions("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", use_cache=False, api_key="", chain="ETH")
    assert len(rows) >= 3
    assert all(r.get("chain") == "ETH" for r in rows)


def test_fetch_transactions_falls_back_to_tron_demo_fixture(monkeypatch):
    monkeypatch.setattr("backend.services.fetcher.settings", SimpleNamespace(etherscan_api_key="", tronscan_api_key="", max_retries=1, backoff_seconds=0))
    rows = fetch_transactions("TTqHYntf2ZFjZo1JJjRsTAMvUjJfttNEYM", use_cache=False, api_key="", chain="TRON")
    assert rows
    assert all(r.get("chain") == "TRON" for r in rows)
    assert all(
        "TTqHYntf2ZFjZo1JJjRsTAMvUjJfttNEYM" in (r.get("from"), r.get("to"))
        for r in rows
    )


def test_cached_fallback_does_not_return_unrelated_wallet_data(monkeypatch):
    monkeypatch.setattr(
        "backend.services.fetcher.settings",
        SimpleNamespace(etherscan_api_key="", tronscan_api_key="", max_retries=1, backoff_seconds=0),
    )
    rows = fetch_transactions(
        "0x0000000000000000000000000000000000000001",
        use_cache=False,
        api_key="",
        chain="ETH",
    )
    assert rows == []


def test_tron_normalizer_handles_live_shape():
    txs = [{
        "hash": "trc123",
        "ownerAddress": "TQn9Y2khJ5nY7UQ6qkV8M8T4nCz4fBfU5w9",
        "toAddress": "TDdvqwbk2zeau23vzuPzenMWdb3h7Vsudu",
        "amount": "1230000",
        "timestamp": 1710000000,
        "tokenInfo": {"symbol": "TRX"},
    }]
    normalized = normalize_tron_raw(txs)
    assert normalized[0]["chain"] == "TRON"
    assert normalized[0]["amount"] == 1.23
    assert normalized[0]["asset"] == "TRX"


def test_fetch_transactions_uses_tronscan_live_path(monkeypatch):
    captured = {}

    def fake_call_with_retry(fn, *args, **kwargs):
        captured["fn"] = fn.__name__
        return [{
            "chain": "TRON",
            "tx_hash": "trc456",
            "from": "TQn9Y2khJ5nY7UQ6qkV8M8T4nCz4fBfU5w9",
            "to": "TDdvqwbk2zeau23vzuPzenMWdb3h7Vsudu",
            "amount": "2500000",
            "timestamp": 1710000000,
        }]

    monkeypatch.setattr("backend.services.fetcher.call_with_retry", fake_call_with_retry)
    monkeypatch.setattr(
        "backend.services.fetcher.settings",
        SimpleNamespace(tronscan_api_key="secret-key", max_retries=1, backoff_seconds=0),
    )

    results = fetch_transactions("TQn9Y2khJ5nY7UQ6qkV8M8T4nCz4fBfU5w9", use_cache=False, api_key="secret-key", chain="TRON")
    assert results[0]["chain"] == "TRON"
    assert captured["fn"] == "fetch_tron_transactions"


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
