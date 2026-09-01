import requests
from datetime import datetime, timezone

from backend.config import settings

BASE_URL = "https://api.etherscan.io/v2/api"


def fetch_eth_transactions(address: str, chainid: int = 1, api_key: str = None):
    """Fetch Ethereum transactions from the Etherscan V2 API and normalize the most relevant fields."""
    api_key = api_key or settings.etherscan_api_key
    params = {
        "chainid": str(chainid),  # V2 API requires chainid as string
        "module": "account",
        "action": "txlist",
        "address": address,
        # Keep the provider response bounded and recent; the trace service
        # applies its own investigator-visible transaction limit afterwards.
        "page": 1,
        "offset": settings.max_trace_transactions,
        "sort": "desc",
        "apikey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=settings.request_timeout)
    data = resp.json()

    if data.get("status") == "0" and "rate limit" in str(data.get("result", "")).lower():
        raise RuntimeError("RATE_LIMIT")
    if data.get("status") == "0" and isinstance(data.get("result"), str) and data["result"].strip():
        raise RuntimeError(f"ETHERSCAN_ERROR: {data['result'][:200]}")

    raw = data.get("result", [])
    if not isinstance(raw, list):
        return []

    normalized = []
    for tx in raw:
        normalized.append({
            "chain": "ETH",
            "tx_hash": tx.get("hash"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "asset": "ETH",
            "amount": float(int(tx.get("value", 0)) / 1e18),
            "timestamp": tx.get("timeStamp"),
            "block": int(tx.get("blockNumber", 0)) if tx.get("blockNumber") is not None else None,
            "source_url": f"https://etherscan.io/tx/{tx.get('hash')}",
        })
    return normalized


def fetch_eth_transaction_by_hash(tx_hash: str, chainid: int = 1, api_key: str = None):
    """Fetch one native ETH transaction by hash and resolve its block timestamp."""
    api_key = api_key or settings.etherscan_api_key
    params = {
        "chainid": str(chainid),  # V2 API requires chainid as string
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash,
        "apikey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=settings.request_timeout)
    data = resp.json()
    if data.get("status") == "0" and "rate limit" in str(data.get("result", "")).lower():
        raise RuntimeError("RATE_LIMIT")
    if data.get("status") == "0" and isinstance(data.get("result"), str) and data["result"].strip():
        raise RuntimeError(f"ETHERSCAN_ERROR: {data['result'][:200]}")
    transaction = data.get("result")
    if not isinstance(transaction, dict):
        return []

    block_number = transaction.get("blockNumber")
    timestamp = None
    if block_number:
        block_params = {
            "chainid": str(chainid),  # V2 API requires chainid as string
            "module": "proxy",
            "action": "eth_getBlockByNumber",
            "tag": block_number,
            "boolean": "false",
            "apikey": api_key,
        }
        block_resp = requests.get(BASE_URL, params=block_params, timeout=settings.request_timeout)
        block_data = block_resp.json()
        block = block_data.get("result") or {}
        block_timestamp = block.get("timestamp")
        if block_timestamp:
            timestamp = datetime.fromtimestamp(
                int(block_timestamp, 16),
                tz=timezone.utc,
            ).isoformat().replace("+00:00", "Z")

    value = transaction.get("value") or "0x0"
    amount = int(value, 16) / 1e18 if isinstance(value, str) else float(value) / 1e18
    return [{
        "chain": "ETH",
        "tx_hash": transaction.get("hash") or tx_hash,
        "from": transaction.get("from"),
        "to": transaction.get("to"),
        "asset": "ETH",
        "amount": amount,
        "timestamp": timestamp,
        "block": int(block_number, 16) if isinstance(block_number, str) else block_number,
        "source_url": f"https://etherscan.io/tx/{transaction.get('hash') or tx_hash}",
    }]
