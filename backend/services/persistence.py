from typing import Any, Dict, List, Optional

from backend.services.sqlite_store import list_cases as sqlite_list_cases
from backend.services.sqlite_store import load_case as sqlite_load_case
from backend.services.sqlite_store import save_case as sqlite_save_case


def save_case(case_id: str, payload: Any, user_id: Optional[int] = None) -> str:
    sqlite_save_case(case_id, payload, user_id=user_id)
    return case_id


def load_case(case_id: str) -> Optional[Dict[str, Any]]:
    return sqlite_load_case(case_id)


def list_cases(user_id: Optional[int] = None) -> List[str]:
    return sqlite_list_cases(user_id=user_id)
