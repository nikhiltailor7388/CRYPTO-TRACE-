import requests

from backend.config import settings

BASE_URL = "https://apilist.tronscanapi.com/api/transaction"


def fetch_tron_transactions(address: str, api_key: str = None, limit: int = 50):
    """Fetch recent outgoing/incoming TRON transactions for a wallet using TronScan."""
    if not address:
        return []

    resolved_key = (api_key or settings.tronscan_api_key or "").strip()
    if not resolved_key:
        raise RuntimeError("NO_TRON_API_KEY")

    params = {
        "address": address,
        "limit": limit,
        "start": 0,
        "sort": "-timestamp",
        "count": "true",
    }
    headers = {"TRON-PRO-API-KEY": resolved_key}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=settings.request_timeout)
    data = resp.json()

    if resp.status_code >= 400:
        raise RuntimeError(f"TRONSCAN_HTTP_{resp.status_code}")
    if not isinstance(data, dict):
        return []

    txs = data.get("data") or []
    if not isinstance(txs, list):
        return []

    normalized = []
    for tx in txs:
        tx_hash = tx.get("hash") or tx.get("tx_hash")
        if not tx_hash:
            continue
        to_candidates = tx.get("toAddressList") or []
        target_address = tx.get("toAddress")
        if isinstance(to_candidates, list) and to_candidates:
            first = to_candidates[0]
            if isinstance(first, dict):
                target_address = first.get("address") or target_address
        normalized.append({
            "chain": "TRON",
            "tx_hash": tx_hash,
            "from": tx.get("ownerAddress") or tx.get("from"),
            "to": target_address or tx.get("to"),
            "amount": float(tx.get("amount") or tx.get("value") or 0) / 1_000_000,
            "asset": (tx.get("tokenInfo") or {}).get("symbol") or tx.get("tokenSymbol") or "TRX",
            "timestamp": tx.get("timestamp") or tx.get("timeStamp"),
            "block": tx.get("block"),
            "source_url": f"https://tronscan.org/#/transaction/{tx_hash}",
        })
    return normalized
