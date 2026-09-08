import requests
from datetime import datetime, timezone

from backend.config import settings

BASE_URL = "https://api.etherscan.io/v2/api"


def fetch_eth_transactions(address: str, chainid: int = 1, api_key: str = None, limit: int = None, asset: str = None):
    """Fetch Ethereum transactions from the Etherscan V2 API and normalize the most relevant fields."""
    api_key = api_key or settings.etherscan_api_key
    # Fetch in provider-supported pages.  One extra record lets the trace
    # layer prove that its own safety cap omitted data instead of treating an
    # exact count as an incomplete result.
    requested = limit or (settings.max_trace_transactions + 1)
    page_size = min(100, requested)
    raw = []
    for page in range(1, (requested + page_size - 1) // page_size + 1):
        params = {
            "chainid": str(chainid), "module": "account", "action": "tokentx" if asset and asset.upper() not in {"ETH", "ETHEREUM"} else "txlist",
            "address": address, "page": page, "offset": page_size,
            "sort": "desc", "apikey": api_key,
        }
        try:
            resp = requests.get(BASE_URL, params=params, timeout=settings.request_timeout)
            data = resp.json()
        except requests.RequestException as exc:
            raise RuntimeError("ETHERSCAN_NETWORK: request failed") from exc
        except ValueError as exc:
            raise RuntimeError("ETHERSCAN_MALFORMED_RESPONSE: invalid JSON") from exc
        if data.get("status") == "0" and "rate limit" in str(data.get("result", "")).lower():
            raise RuntimeError("RATE_LIMIT")
        if data.get("status") == "0" and isinstance(data.get("result"), str) and data["result"].strip() and "no transactions found" not in data["result"].lower():
            raise RuntimeError(f"ETHERSCAN_ERROR: {data['result'][:200]}")
        page_records = data.get("result", [])
        if not isinstance(page_records, list):
            return []
        raw.extend(page_records)
        if len(page_records) < page_size or len(raw) >= requested:
            break
    raw = raw[:requested]

    normalized = []
    for tx in raw:
        is_token = "tokenDecimal" in tx or "tokenSymbol" in tx
        decimals = int(tx.get("tokenDecimal", 18)) if is_token else 18
        normalized.append({
            "chain": "ETH",
            "tx_hash": tx.get("hash"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "asset": tx.get("tokenSymbol") if is_token else "ETH",
            "amount": float(int(tx.get("value", 0)) / (10 ** decimals)),
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
