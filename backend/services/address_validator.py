import re
import hashlib

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TRON_ADDRESS_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


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
        address = str(value).strip() if value is not None else ""
        if not address or not _TRON_ADDRESS_RE.match(address):
            return False
        try:
            decoded = 0
            for character in address:
                decoded = decoded * 58 + _BASE58_ALPHABET.index(character)
            payload = decoded.to_bytes((decoded.bit_length() + 7) // 8, "big")
            payload = b"\x00" * (len(address) - len(address.lstrip("1"))) + payload
        except (ValueError, OverflowError):
            return False
        if len(payload) != 25 or payload[0] != 0x41:
            return False
        checksum = hashlib.sha256(hashlib.sha256(payload[:-4]).digest()).digest()[:4]
        return payload[-4:] == checksum
    return False
