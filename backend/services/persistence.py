from typing import Any, Dict, List, Optional

from backend.services.sqlite_store import list_cases as sqlite_list_cases
from backend.services.sqlite_store import load_case as sqlite_load_case
from backend.services.sqlite_store import save_case as sqlite_save_case
from backend.services.fraud_detector import apply_canonical_risk


def save_case(case_id: str, payload: Any, user_id: Optional[int] = None) -> str:
    if isinstance(payload, dict):
        apply_canonical_risk(payload)
    sqlite_save_case(case_id, payload, user_id=user_id)
    return case_id


def load_case(case_id: str) -> Optional[Dict[str, Any]]:
    payload = sqlite_load_case(case_id)
    return apply_canonical_risk(payload) if isinstance(payload, dict) else payload


def list_cases(user_id: Optional[int] = None) -> List[str]:
    return sqlite_list_cases(user_id=user_id)
