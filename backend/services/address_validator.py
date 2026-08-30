import re

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def normalize_address(value: str) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    return value.lower() if value else ""


def is_valid_eth_address(value: str) -> bool:
    if value is None:
        return False
    value = str(value).strip()
    return bool(value) and bool(_ETH_ADDRESS_RE.match(value))
