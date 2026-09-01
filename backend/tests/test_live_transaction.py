from types import SimpleNamespace

from backend.adapters import etherscan_adapter
from backend.api.trace_impl import TraceRequest, trace


def test_etherscan_transaction_lookup_preserves_transaction_fields(monkeypatch):
    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def fake_get(url, params, timeout):
        calls.append(params)
        if params["action"] == "eth_getTransactionByHash":
            return Response({
                "result": {
                    "hash": params["txhash"],
                    "from": "0x1111111111111111111111111111111111111111",
                    "to": "0x2222222222222222222222222222222222222222",
                    "value": "0xde0b6b3a7640000",
                    "blockNumber": "0x10",
                }
            })
        return Response({"result": {"timestamp": "0x65a1bc00"}})

    monkeypatch.setattr(etherscan_adapter.requests, "get", fake_get)
    tx_hash = "0x" + "a" * 64
    result = etherscan_adapter.fetch_eth_transaction_by_hash(tx_hash, api_key="test-key")

    assert result == [{
        "chain": "ETH",
        "tx_hash": tx_hash,
        "from": "0x1111111111111111111111111111111111111111",
        "to": "0x2222222222222222222222222222222222222222",
        "asset": "ETH",
        "amount": 1.0,
        "timestamp": "2024-01-12T22:24:00Z",
        "block": 16,
        "source_url": f"https://etherscan.io/tx/{tx_hash}",
    }]
    assert calls[0]["action"] == "eth_getTransactionByHash"
    assert calls[0]["txhash"] == tx_hash


def test_live_trace_uses_two_different_transaction_hashes(monkeypatch):
    wallet = "0x1111111111111111111111111111111111111111"
    transactions = {
        "0x" + "a" * 64: {
            "tx_hash": "0x" + "a" * 64,
            "from": wallet,
            "to": "0x2222222222222222222222222222222222222222",
            "amount": 1.0,
            "asset": "ETH",
            "timestamp": "2024-01-01T00:00:00Z",
            "block": 1,
        },
        "0x" + "b" * 64: {
            "tx_hash": "0x" + "b" * 64,
            "from": wallet,
            "to": "0x3333333333333333333333333333333333333333",
            "amount": 2.0,
            "asset": "ETH",
            "timestamp": "2024-01-02T00:00:00Z",
            "block": 2,
        },
    }

    def fake_fetch(address, use_cache=True, api_key=None, chain="ETH", tx_hash=None):
        return [transactions[tx_hash]] if tx_hash else []

    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr("backend.api.trace_impl.fetch_transactions", fake_fetch)
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    responses = [
        trace(
            TraceRequest(case_id=f"LIVE-{suffix}", wallets=[wallet], tx_hash=tx_hash),
            SimpleNamespace(headers={}),
        )
        for suffix, tx_hash in (("A", "0x" + "a" * 64), ("B", "0x" + "b" * 64))
    ]

    assert responses[0]["data_source"] == "live"
    assert responses[1]["data_source"] == "live"
    assert responses[0]["seed_tx"]["tx_hash"] != responses[1]["seed_tx"]["tx_hash"]
    assert responses[0]["evidence"][0]["tx_hash"] != responses[1]["evidence"][0]["tx_hash"]
    assert responses[0]["graph"]["edges"][0]["tx_hash"] != responses[1]["graph"]["edges"][0]["tx_hash"]


def test_live_trace_with_empty_transaction_hash_uses_wallet_history(monkeypatch):
    wallet = "0x1111111111111111111111111111111111111111"

    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(
        "backend.api.trace_impl.fetch_transactions",
        lambda *args, **kwargs: [{
            "tx_hash": "0x" + "c" * 64,
            "from": wallet,
            "to": "0x2222222222222222222222222222222222222222",
            "amount": 1.0,
            "asset": "ETH",
            "timestamp": "2024-01-01T00:00:00Z",
            "block": 1,
        }],
    )
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace(
        TraceRequest(case_id="LIVE-EMPTY-HASH", wallets=[wallet], tx_hash=""),
        SimpleNamespace(headers={}),
    )

    assert response["data_source"] == "live"
    assert response["seed_tx"] is None
    assert response["evidence"][0]["tx_hash"] == "0x" + "c" * 64


def test_live_trace_rejects_unknown_transaction_hash(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(
        "backend.api.trace_impl.fetch_transactions",
        lambda *args, **kwargs: [],
    )

    try:
        trace(
            TraceRequest(
                case_id="LIVE-UNKNOWN-HASH",
                wallets=["0x1111111111111111111111111111111111111111"],
                tx_hash="0x" + "d" * 64,
            ),
            SimpleNamespace(headers={}),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "transaction" in exc.detail.lower()
    else:
        raise AssertionError("Expected an unknown live transaction hash to return 404")


def test_demo_fetch_keeps_using_cache(monkeypatch):
    from backend.services import fetcher

    cached = [{"tx_hash": "demo-hash", "from": "0xvictim", "to": "0xreceiver", "amount": 1.0}]
    monkeypatch.setattr(fetcher, "fetch_transactions_from_cache", lambda **kwargs: cached)
    monkeypatch.setattr(
        fetcher,
        "fetch_eth_transaction_by_hash",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live lookup used in demo mode")),
    )

    assert fetcher.fetch_transactions(
        "0x1111111111111111111111111111111111111111",
        use_cache=True,
        tx_hash="0x" + "e" * 64,
    ) == cached


def test_rate_limit_falls_back_to_demo_data(monkeypatch):
    from backend.api import trace_impl

    wallet = "0x1111111111111111111111111111111111111111"
    cached = [{
        "tx_hash": "demo-rate-limit",
        "from": wallet,
        "to": "0x2222222222222222222222222222222222222222",
        "amount": 1.0,
        "asset": "ETH",
        "timestamp": "2024-01-01T00:00:00Z",
        "block": 1,
    }]
    calls = []

    def fake_fetch(address, use_cache=True, **kwargs):
        calls.append(use_cache)
        if not use_cache:
            raise RuntimeError("RATE_LIMIT")
        return cached

    monkeypatch.setenv("USE_ETHERSCAN", "true")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(trace_impl, "fetch_transactions", fake_fetch)
    monkeypatch.setattr("backend.services.persistence.save_case", lambda *args, **kwargs: None)

    response = trace_impl.trace(
        trace_impl.TraceRequest(case_id="LIVE-RATE-LIMIT", wallets=[wallet]),
        SimpleNamespace(headers={}),
    )

    assert response["data_source"] == "synthetic demo data"
    assert response["fallback_used"] is True
    assert calls[0:2] == [False, True]
    assert all(call is True for call in calls[1:])


def test_live_configuration_error_is_not_hidden(monkeypatch):
    from backend.services import fetcher

    monkeypatch.setattr(fetcher, "settings", SimpleNamespace(etherscan_api_key=""))
    try:
        fetcher.fetch_transactions(
            "0x1111111111111111111111111111111111111111",
            use_cache=False,
            api_key=None,
        )
    except RuntimeError as exc:
        assert str(exc).startswith("ETHERSCAN_CONFIGURATION:")
    else:
        raise AssertionError("Expected missing live configuration to remain visible")


def test_cache_does_not_return_fixture_data_for_an_unrelated_wallet():
    from backend.services.fetcher import fetch_transactions

    assert fetch_transactions("0x1111111111111111111111111111111111111111", use_cache=True) == []
