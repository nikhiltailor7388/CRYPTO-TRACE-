from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.services.auth import create_token, decode_token, get_bearer_token, hash_password, verify_password
from backend.services.sqlite_store import create_user, get_user_by_email, get_user_by_id

router = APIRouter(prefix="/auth")
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    full_name: str


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=409, detail="User already exists. Please login instead.")
    user = create_user(payload.email, hash_password(payload.password), payload.full_name)
    token = create_token(user["id"], user["email"])
    return AuthResponse(token=token, email=user["email"], full_name=user["full_name"] or "")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["id"], user["email"])
    return AuthResponse(token=token, email=user["email"], full_name=user["full_name"] or "")


@router.get("/me")
def current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        raw_token = get_bearer_token(token.credentials)
        data = decode_token(raw_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(int(data["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "email": user["email"], "full_name": user["full_name"] or ""}
