import os
from urllib.parse import urlparse

from fastapi import HTTPException, Request, status


def _trusted_origins() -> set[str]:
    raw = os.getenv("TRUSTED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    return {origin.strip() for origin in raw.split(",") if origin.strip()}


def _origin_from_referer(referer: str) -> str | None:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def verify_same_origin(request: Request) -> None:
    """CSRF defense for cookie-authenticated mutation endpoints.
    SameSite=Lax is defense-in-depth, not sufficient on its own (OWASP) —
    this exact-matches Origin (falling back to Referer's origin) against
    a trusted allowlist. No Origin and no Referer -> reject, never allow.
    """
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        origin = _origin_from_referer(referer) if referer else None
    if origin not in _trusted_origins():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not trusted")
