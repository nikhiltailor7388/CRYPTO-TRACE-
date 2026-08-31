import json
from pathlib import Path
from typing import Any, Dict, List

from backend.adapters.etherscan_adapter import fetch_eth_transactions
from backend.adapters.resilient import call_with_retry
from backend.adapters.tronscan_adapter import fetch_tron_transactions
from backend.config import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_FILE = DATA_DIR / "eth_cache.json"
TRON_CACHE_FILE = DATA_DIR / "tron_cache.json"
CHAIN_TO_ID = {
    "ETH": 1,
    "ETHEREUM": 1,
    "BSC": 56,
    "BINANCE": 56,
    "POLYGON": 137,
    "MATIC": 137,
    "ARBITRUM": 42161,
    "BASE": 8453,
    "TRON": 1,
}


def fetch_transactions_from_cache(chain: str = "ETH") -> List[Dict[str, Any]]:
    chain_key = str(chain or "ETH").upper().replace(" ", "_")
    cache_path = TRON_CACHE_FILE if chain_key.startswith("TRON") else CACHE_FILE
    if not cache_path.exists():
        return []
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _filter_cached_transactions(rows: List[Dict[str, Any]], address: str) -> List[Dict[str, Any]]:
    """Return only cached transactions involving the requested wallet."""
    normalized_address = str(address or "").strip().lower()
    if not normalized_address:
        return []
    return [
        row
        for row in rows
        if str(row.get("from") or "").strip().lower() == normalized_address
        or str(row.get("to") or "").strip().lower() == normalized_address
    ]


def fetch_transactions_etherscan(address: str, api_key: str, chainid: int = 1) -> List[Dict[str, Any]]:
    """Fetch transactions using the Etherscan V2 endpoint and a retry-aware wrapper."""
    try:
        results = call_with_retry(
            fetch_eth_transactions,
            address,
            chainid=chainid,
            api_key=api_key or settings.etherscan_api_key,
            max_attempts=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
        if isinstance(results, list):
            for item in results:
                item.setdefault("chain", "ETH" if chainid == 1 else str(chainid))
            return results
        return []
    except RuntimeError:
        return _filter_cached_transactions(fetch_transactions_from_cache(chain="ETH"), address)


def fetch_transactions_tronscan(address: str, api_key: str = None) -> List[Dict[str, Any]]:
    """Fetch transactions using the TronScan API with graceful fallback when live access is unavailable."""
    try:
        results = call_with_retry(
            fetch_tron_transactions,
            address,
            api_key=api_key or settings.tronscan_api_key,
            max_attempts=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
        if isinstance(results, list):
            for item in results:
                item.setdefault("chain", "TRON")
            return results
        return []
    except RuntimeError:
        return []


def fetch_transactions(address: str, use_cache: bool = True, api_key: str = None, chain: str = "ETH") -> List[Dict[str, Any]]:
    """Public function to fetch transactions for an address."""
    chain_key = str(chain or "ETH").upper().replace(" ", "_")
    chain_id = CHAIN_TO_ID.get(chain_key, 1)

    if chain_key.startswith("TRON"):
        if use_cache or not (api_key or settings.tronscan_api_key):
            return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)
        try:
            results = fetch_transactions_tronscan(address, api_key or settings.tronscan_api_key)
            if not results:
                return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)
            return results
        except Exception:
            return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)

    if use_cache or not (api_key or settings.etherscan_api_key):
        return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)

    try:
        results = fetch_transactions_etherscan(address, api_key or settings.etherscan_api_key, chainid=chain_id)
        if not results:
            return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)
        return results
    except Exception:
        return _filter_cached_transactions(fetch_transactions_from_cache(chain=chain_key), address)
