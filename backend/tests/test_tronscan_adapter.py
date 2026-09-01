from backend.adapters import tronscan_adapter


class Response:
    ok = True
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_tronscan_history_normalizes_to_common_transaction(monkeypatch):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return Response({"data": [{
            "hash": "tron-hash", "timestamp": 1704067200000, "block": 123,
            "ownerAddress": "TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV",
            "toAddress": "TVjsyZ7fYF3qLF6BQgPmTEZy1xrNL6wyKz",
            "contractType": 1, "contractData": {"amount": 1500000},
        }]})

    monkeypatch.setattr(tronscan_adapter.requests, "get", fake_get)
    result = tronscan_adapter.fetch_tron_transactions("TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV", api_key="test-key", limit=25)
    assert result == [{
        "chain": "TRON", "tx_hash": "tron-hash", "from": "TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV",
        "to": "TVjsyZ7fYF3qLF6BQgPmTEZy1xrNL6wyKz", "asset": "TRX", "amount": 1.5,
        "timestamp": "2024-01-01T00:00:00Z", "block": 123,
        "source_url": "https://tronscan.org/#/transaction/tron-hash",
    }]
    assert seen["headers"] == {"TRON-PRO-API-KEY": "test-key"}
    assert seen["params"]["address"] == "TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV"


def test_tronscan_excludes_non_native_and_zero_value_records(monkeypatch):
    monkeypatch.setattr(tronscan_adapter.requests, "get", lambda *args, **kwargs: Response({"data": [
        {"hash": "token", "contractType": 31, "ownerAddress": "TA", "toAddress": "TB", "contractData": {"amount": 1}},
        {"hash": "zero", "contractType": 1, "ownerAddress": "TA", "toAddress": "TB", "contractData": {"amount": 0}},
    ]}))
    assert tronscan_adapter.fetch_tron_transactions("TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV", api_key="test-key") == []


def test_tronscan_rate_limit_keeps_retry_after_without_exposing_key(monkeypatch):
    class LimitedResponse(Response):
        ok = False
        status_code = 429
        headers = {"Retry-After": "7"}

    monkeypatch.setattr(tronscan_adapter.requests, "get", lambda *args, **kwargs: LimitedResponse({}))
    try:
        tronscan_adapter.fetch_tron_transactions("TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV", api_key="test-key")
    except RuntimeError as exc:
        assert str(exc) == "TRONSCAN_RATE_LIMIT; retry after 7s"
    else:
        raise AssertionError("Expected the provider rate limit to remain visible")


def test_tronscan_lookup_accepts_top_level_transaction_with_string_data(monkeypatch):
    monkeypatch.setattr(tronscan_adapter.requests, "get", lambda *args, **kwargs: Response({
        "hash": "lookup-hash", "timestamp": 1704067200000, "block": 123,
        "ownerAddress": "TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV",
        "toAddress": "TVjsyZ7fYF3qLF6BQgPmTEZy1xrNL6wyKz",
        "contractType": 1, "contractData": {"amount": 1500000},
        "data": "a9059cbb",  # Transaction input, not a list envelope.
    }))
    result = tronscan_adapter.fetch_tron_transaction_by_hash("lookup-hash", api_key="test-key")
    assert result[0]["tx_hash"] == "lookup-hash"
    assert result[0]["amount"] == 1.5


def test_tronscan_distinguishes_empty_history_and_json_api_error(monkeypatch):
    monkeypatch.setattr(tronscan_adapter.requests, "get", lambda *args, **kwargs: Response({"data": []}))
    assert tronscan_adapter.fetch_tron_transactions("TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV", api_key="test-key") == []

    monkeypatch.setattr(tronscan_adapter.requests, "get", lambda *args, **kwargs: Response({"success": False, "code": 1001, "message": "invalid request"}))
    try:
        tronscan_adapter.fetch_tron_transactions("TNYgZhaqeJRhdWwpqM1WxJU88L4GxW9BsV", api_key="test-key")
    except RuntimeError as exc:
        assert str(exc) == "TRONSCAN_API_ERROR: invalid request"
    else:
        raise AssertionError("Expected an API error envelope to remain visible")
