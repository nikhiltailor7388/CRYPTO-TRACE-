import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
VASP_FILE = DATA_DIR / "data" / "vasp_labels.json"
ALT_VASP_FILE = DATA_DIR / "vasp" / "vasp_labels.json"


def _normalise_labels(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        out = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            addr = (item.get("address") or "").lower()
            if addr:
                out[addr] = item
        return out
    return {}


def load_vasp_labels():
    for candidate in (VASP_FILE, ALT_VASP_FILE):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return _normalise_labels(json.load(f))
        except Exception:
            continue
    return {}


def match_vasp_for_address(address: str, vasp_labels: dict, chain: str = None):
    if not address:
        return None
    key = str(address).lower().strip()
    if not key:
        return None
    match = vasp_labels.get(key)
    if match and chain and str(match.get("chain") or "").upper() != str(chain).upper():
        return None
    return match
