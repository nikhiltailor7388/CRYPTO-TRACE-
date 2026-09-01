import json
from pathlib import Path
from typing import Any, Dict, List

from backend.adapters.etherscan_adapter import fetch_eth_transaction_by_hash, fetch_eth_transactions
from backend.adapters.tronscan_adapter import fetch_tron_transaction_by_hash, fetch_tron_transactions
from backend.adapters.resilient import call_with_retry
from backend.config import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_FILE = DATA_DIR / "eth_cache.json"
CHAIN_TO_ID = {
    "ETH": 1,
    "ETHEREUM": 1,
    "BSC": 56,
    "BINANCE": 56,
    "POLYGON": 137,
    "MATIC": 137,
    "ARBITRUM": 42161,
    "BASE": 8453,
}
TRON_CHAINS = {"TRON", "TRX"}


def fetch_transactions_from_cache(address: str = None, chain: str = "ETH", tx_hash: str = None) -> List[Dict[str, Any]]:
    """Return only fixture records connected to the requested seed."""
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    chain_key = str(chain or "ETH").upper().replace(" ", "_")
    requested_address = str(address or "").lower().strip()
    requested_hash = str(tx_hash or "").lower().strip()
    return [
        item for item in records
        if (not requested_address or requested_address in {
            str(item.get("from") or "").lower(), str(item.get("to") or "").lower()
        })
        and (not requested_hash or str(item.get("tx_hash") or item.get("hash") or "").lower() == requested_hash)
        and str(item.get("chain") or "ETH").upper() == chain_key
    ]


def fetch_transactions_etherscan(address: str, api_key: str, chainid: int = 1, tx_hash: str = None) -> List[Dict[str, Any]]:
    """Fetch transactions using the Etherscan V2 endpoint and a retry-aware wrapper."""
    try:
        if tx_hash:
            results = call_with_retry(
                fetch_eth_transaction_by_hash,
                tx_hash,
                chainid=chainid,
                api_key=api_key or settings.etherscan_api_key,
                max_attempts=settings.max_retries,
                backoff_seconds=settings.backoff_seconds,
            )
        else:
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
        raise


def fetch_transactions(address: str, use_cache: bool = True, api_key: str = None, chain: str = "ETH", tx_hash: str = None) -> List[Dict[str, Any]]:
    """Public function to fetch transactions for an address.

    In live investigation mode the system must not silently fall back to demo cache data. If the live lookup fails or the
    address has no real history, the caller must surface an explicit error so the UI can show it clearly.
    """
    chain_key = str(chain or "ETH").upper().replace(" ", "_")
    chain_id = CHAIN_TO_ID.get(chain_key, 1)

    if use_cache:
        if chain_key in TRON_CHAINS:
            return []
        return fetch_transactions_from_cache(address=address, chain=chain_key, tx_hash=tx_hash)

    if chain_key in TRON_CHAINS:
        tronscan_key = api_key or getattr(settings, "tronscan_api_key", "")
        if not tronscan_key:
            raise RuntimeError("TRONSCAN_CONFIGURATION: TRONSCAN_API_KEY is required for live TRON mode")
        return (
            fetch_tron_transaction_by_hash(tx_hash, api_key=tronscan_key)
            if tx_hash else fetch_tron_transactions(
                address,
                api_key=tronscan_key,
                limit=min(settings.tronscan_page_size, settings.max_trace_transactions),
            )
        )

    if not (api_key or settings.etherscan_api_key):
        raise RuntimeError("ETHERSCAN_CONFIGURATION: ETHERSCAN_API_KEY is required for live mode")

    results = fetch_transactions_etherscan(
        address,
        api_key or settings.etherscan_api_key,
        chainid=chain_id,
        tx_hash=tx_hash,
    )
    if not results:
        return []
    return results
