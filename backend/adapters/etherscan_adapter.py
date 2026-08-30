import requests

from backend.config import settings

BASE_URL = "https://api.etherscan.io/v2/api"


def fetch_eth_transactions(address: str, chainid: int = 1, api_key: str = None):
    """Fetch Ethereum transactions from the Etherscan V2 API and normalize the most relevant fields."""
    api_key = api_key or settings.etherscan_api_key
    params = {
        "chainid": chainid,
        "module": "account",
        "action": "txlist",
        "address": address,
        "sort": "asc",
        "apikey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=settings.request_timeout)
    data = resp.json()

    if data.get("status") == "0" and "rate limit" in str(data.get("result", "")).lower():
        raise RuntimeError("RATE_LIMIT")

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
