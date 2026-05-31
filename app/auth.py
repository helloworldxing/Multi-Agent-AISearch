from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status

from app.db import get_conn

_ALGO = "HS256"
_TOKEN_TTL_HOURS = 24 * 7  # 一周


def _load_secret() -> str:
    env_secret = os.environ.get("APP_JWT_SECRET")
    if env_secret:
        return env_secret
    secret_file = Path(__file__).parent.parent / "data" / ".jwt_secret"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    new_secret = secrets.token_urlsafe(48)
    secret_file.write_text(new_secret, encoding="utf-8")
    return new_secret


_SECRET = _load_secret()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def decode_token(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None


def _user_from_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    if token.lower().startswith("bearer "):
        token = token[7:]
    payload = decode_token(token)
    if not payload:
        return None
    user_id = int(payload.get("sub", 0))
    if not user_id:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return dict(row)


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency：要求登录，否则 401。"""
    user = _user_from_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或令牌已过期",
        )
    return user


def optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    return _user_from_token(authorization)


def user_from_query_token(token: Optional[str]) -> Optional[dict]:
    """SSE 场景下从 query 参数读取 token（EventSource 不支持自定义请求头）。"""
    return _user_from_token(token)
