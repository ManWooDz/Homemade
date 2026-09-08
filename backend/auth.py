import hashlib
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import update
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import RefreshToken, User

load_dotenv()

# passlib's CryptContext is broken against bcrypt>=4.0 (reads a removed
# __about__.__version__ attr) — call bcrypt directly instead. See
# spec.md PostgreSQL migration notes.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30


def _parse_bool_env(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() == "true"


COOKIE_SECURE = _parse_bool_env("COOKIE_SECURE", "false")

if not JWT_SECRET_KEY or len(JWT_SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY missing or too short (<32 bytes) in backend/.env — "
        'generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(user_id, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def _decode_token(token: str, expected_type: str) -> dict | None:
    """Decode + validate a JWT. Returns {"user_id": int, "jti": str} on
    success, or None on ANY validation failure — never raises, so callers
    turn every failure into a 401 uniformly."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    jti = payload.get("jti")
    if not jti:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    return {"user_id": user_id, "jti": jti}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    if not token:
        raise unauthorized
    claims = _decode_token(token, expected_type="access")
    if claims is None:
        raise unauthorized
    user = db.get(User, claims["user_id"])
    if user is None:
        raise unauthorized
    return user


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/api",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/api/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/api")
    response.delete_cookie("refresh_token", path="/api/auth")


def rotate_refresh_token(db: Session, raw_refresh_token: str) -> tuple[str, str] | None:
    """Atomically rotate a refresh token. Returns (new_access, new_refresh)
    on success, or None if the token is invalid/expired/already used. The
    compare-and-set UPDATE (revoked_at IS NULL AND expires_at > now) is
    what makes this safe under concurrent requests — not merely wrapping
    it in a transaction."""
    claims = _decode_token(raw_refresh_token, expected_type="refresh")
    if claims is None:
        return None

    now = datetime.now(timezone.utc)
    token_hash = hash_token(raw_refresh_token)
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
        .returning(RefreshToken.user_id)
    )
    row = result.first()
    if row is None:
        db.rollback()
        return None

    user_id = row[0]
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(new_refresh),
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return new_access, new_refresh


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    """Best-effort revoke for logout. Never raises for a bad/missing/
    already-revoked token (hashing works on the raw string regardless of
    whether it's a valid JWT) — only a genuine DB failure propagates, and
    the caller (main.py's /logout) decides how to respond to that."""
    token_hash = hash_token(raw_refresh_token)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
