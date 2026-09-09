from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.auth import decode_token, get_bearer_token
from backend.services.case_access import require_case_access
from backend.services.sqlite_store import get_user_by_id, list_case_metadata
from backend.services.persistence import load_case

router = APIRouter()
security = HTTPBearer(auto_error=False)


def current_user_or_none(token: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not token:
        return None
    try:
        user_id = int(decode_token(get_bearer_token(token.credentials))["sub"])
        user = get_user_by_id(user_id)
        if not user:
            return None
        return user
    except Exception:
        return None


@router.get("/cases")
def list_cases(user: Optional[Dict[str, Any]] = Depends(current_user_or_none)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication is required to list private cases")
    rows = list_case_metadata(user["id"])
    result: List[Dict[str, Any]] = []
    for row in rows:
        case_id = row["case_id"]
        payload = load_case(case_id) or {}
        result.append({
            "case_id": case_id,
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "summary": payload.get("summary", {}),
            "risk_score": payload.get("summary", {}).get("risk_score"),
        })
    return {"cases": result}


@router.get("/cases/{case_id}")
def get_case(case_id: str, user: Optional[Dict[str, Any]] = Depends(current_user_or_none)):
    require_case_access(case_id, user)
    payload = load_case(case_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Case not found")
    payload.pop("user_id", None)
    return payload
