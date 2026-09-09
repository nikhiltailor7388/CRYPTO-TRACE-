from typing import Any, Dict, Optional

from fastapi import HTTPException

from backend.services.sqlite_store import get_case_metadata


def require_case_access(case_id: str, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return case metadata only when the caller may access this saved case."""
    metadata = get_case_metadata(case_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Case not found")
    if metadata.get("is_public"):
        return metadata
    if not user:
        raise HTTPException(status_code=401, detail="Authentication is required to access this private case")
    if metadata.get("user_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return metadata
