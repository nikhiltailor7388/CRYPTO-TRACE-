import re

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TRON_ADDRESS_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


def normalize_address(value: str, chain: str = "ETH") -> str:
    """Return the comparison form for an address without corrupting TRON Base58.

    EVM addresses are case-insensitive; TRON Base58 addresses are not.
    """
    if value is None:
        return ""
    value = str(value).strip()
    return value if str(chain or "ETH").upper().replace(" ", "_") in {"TRON", "TRX"} else value.lower()


def is_valid_eth_address(value: str) -> bool:
    if value is None:
        return False
    value = str(value).strip()
    return bool(value) and bool(_ETH_ADDRESS_RE.match(value))


def is_valid_address(value: str, chain: str) -> bool:
    """Validate only chains the trace API can actually retrieve."""
    chain_key = str(chain or "ETH").upper().replace(" ", "_")
    if chain_key in {"ETH", "ETHEREUM", "BSC", "BINANCE", "POLYGON", "MATIC", "ARBITRUM", "BASE"}:
        return is_valid_eth_address(value)
    if chain_key in {"TRON", "TRX"}:
        return bool(value) and bool(_TRON_ADDRESS_RE.match(str(value).strip()))
    return False
