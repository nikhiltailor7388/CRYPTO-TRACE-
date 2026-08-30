import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "cryptotrace-development-secret-key-change-me-32")
JWT_ALGORITHM = "HS256"
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "240"))


def hash_password(password: str) -> str:
    salt = os.getenv("PASSWORD_SALT", "cryptotrace-salt")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_token(user_id: int, email: str) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=JWT_TTL_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_bearer_token(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise ValueError("Missing bearer token")
    value = auth_header.strip()
    if value.lower().startswith("bearer "):
        value = value.split(" ", 1)[1].strip()
    if not value:
        raise ValueError("Missing bearer token")
    return value
