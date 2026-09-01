"""Read-only TronScan mainnet adapter.

This module owns TronScan request/response handling; callers receive the
project's common transaction dictionaries and never receive API credentials.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from backend.config import settings

BASE_URL = "https://apilist.tronscanapi.com"
EXPLORER_URL = "https://tronscan.org/#/transaction/"


def _provider_error(response: requests.Response) -> None:
    if response.status_code in {401, 403}:
        raise RuntimeError("TRONSCAN_AUTH: TronScan rejected the configured API key")
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        suffix = f"; retry after {retry_after}s" if retry_after else ""
        raise RuntimeError(f"TRONSCAN_RATE_LIMIT{suffix}")
    if response.status_code >= 500:
        raise RuntimeError(f"TRONSCAN_UPSTREAM: HTTP {response.status_code}")
    if not response.ok:
        raise RuntimeError(f"TRONSCAN_ERROR: HTTP {response.status_code}")


def _as_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None


def _normalise_transaction(transaction: Dict[str, Any]) -> Dict[str, Any] | None:
    contract = transaction.get("contractData") or transaction.get("contract_data") or {}
    contract_type = transaction.get("contractType") or transaction.get("contract_type") or contract.get("type")
    # The existing EVM path traces native transfers only. Keep TRON equivalent
    # until a token-transfer provider path is added deliberately.
    if contract_type not in {None, 1, "1", "TransferContract"}:
        return None
    tx_hash = transaction.get("hash") or transaction.get("txID") or transaction.get("tx_hash")
    from_address = transaction.get("ownerAddress") or transaction.get("from") or contract.get("owner_address")
    to_address = transaction.get("toAddress") or transaction.get("transferToAddress") or transaction.get("to") or contract.get("to_address")
    atomic_amount = contract.get("amount", transaction.get("amount"))
    try:
        amount = float(atomic_amount) / 1_000_000
    except (TypeError, ValueError):
        return None
    if not tx_hash or not from_address or not to_address or amount <= 0:
        return None
    return {
        "chain": "TRON",
        "tx_hash": str(tx_hash),
        "from": str(from_address),
        "to": str(to_address),
        "asset": "TRX",
        "amount": amount,
        "timestamp": _as_timestamp(transaction.get("timestamp") or transaction.get("block_timestamp")),
        "block": transaction.get("block") or transaction.get("blockNumber"),
        "source_url": f"{EXPLORER_URL}{tx_hash}",
    }


def _payload_error(payload: Any) -> str | None:
    """Return a safe provider error summary for a JSON error envelope."""
    if not isinstance(payload, dict):
        return None
    message = payload.get("message") or payload.get("msg") or payload.get("error")
    failed = payload.get("success") is False or payload.get("status") in {"error", "fail", False}
    if message and (failed or payload.get("code") not in (None, 0, "0")):
        return str(message)[:200]
    return None


def _parse_transaction_list(payload: Any) -> List[Dict[str, Any]]:
    provider_error = _payload_error(payload)
    if provider_error:
        raise RuntimeError(f"TRONSCAN_API_ERROR: {provider_error}")
    if not isinstance(payload, dict):
        raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: expected a JSON object")
    records = payload.get("data")
    if records is None:
        # A well-formed empty history may omit data entirely.
        return []
    if not isinstance(records, list):
        raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: expected a transaction list")
    return [normalised for item in records if isinstance(item, dict) and (normalised := _normalise_transaction(item))]


def _parse_transaction_lookup(payload: Any) -> List[Dict[str, Any]]:
    provider_error = _payload_error(payload)
    if provider_error:
        raise RuntimeError(f"TRONSCAN_API_ERROR: {provider_error}")
    if not isinstance(payload, dict):
        raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: expected a JSON object")

    # /api/transaction-info returns the transaction at top level. Its `data`
    # field is transaction input and is commonly a string, not a list.
    if payload.get("hash") or payload.get("txID") or payload.get("tx_hash"):
        normalised = _normalise_transaction(payload)
        return [normalised] if normalised else []

    # Accept a list/dict envelope too, so a provider-compatible response does
    # not get confused with the top-level transaction form.
    records = payload.get("data")
    if records is None or records == []:
        return []
    if isinstance(records, dict):
        normalised = _normalise_transaction(records)
        return [normalised] if normalised else []
    if isinstance(records, list):
        return [normalised for item in records if isinstance(item, dict) and (normalised := _normalise_transaction(item))]
    raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: unexpected transaction lookup shape")


def fetch_tron_transactions(address: str, api_key: str = None, limit: int = None) -> List[Dict[str, Any]]:
    key = api_key or getattr(settings, "tronscan_api_key", "")
    if not key:
        raise RuntimeError("TRONSCAN_CONFIGURATION: TRONSCAN_API_KEY is required for live TRON mode")
    try:
        response = requests.get(
            f"{BASE_URL}/api/transaction",
            params={"address": address, "start": 0, "limit": limit or settings.tronscan_page_size, "sort": "-timestamp"},
            headers={"TRON-PRO-API-KEY": key}, timeout=settings.request_timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError("TRONSCAN_NETWORK: request failed") from exc
    _provider_error(response)
    try:
        return _parse_transaction_list(response.json())
    except ValueError as exc:
        raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: invalid JSON") from exc


def fetch_tron_transaction_by_hash(tx_hash: str, api_key: str = None) -> List[Dict[str, Any]]:
    key = api_key or getattr(settings, "tronscan_api_key", "")
    if not key:
        raise RuntimeError("TRONSCAN_CONFIGURATION: TRONSCAN_API_KEY is required for live TRON mode")
    try:
        response = requests.get(
            f"{BASE_URL}/api/transaction-info", params={"hash": tx_hash},
            headers={"TRON-PRO-API-KEY": key}, timeout=settings.request_timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError("TRONSCAN_NETWORK: request failed") from exc
    _provider_error(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("TRONSCAN_MALFORMED_RESPONSE: invalid JSON") from exc
    return _parse_transaction_lookup(payload)
