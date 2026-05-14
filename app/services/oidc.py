import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

_discovery_cache: dict[str, Any] | None = None
_STATE_TTL_MIN = 10
_STATE_ALG = "HS256"


async def get_discovery() -> dict:
    global _discovery_cache
    if _discovery_cache is None:
        url = settings.OIDC_ISSUER_URL.rstrip("/") + "/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            r.raise_for_status()
            _discovery_cache = r.json()
    return _discovery_cache


def make_state() -> str:
    payload = {"exp": datetime.utcnow() + timedelta(minutes=_STATE_TTL_MIN), "purpose": "oidc-state"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_STATE_ALG)


def verify_state(token: str) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_STATE_ALG])
        return payload.get("purpose") == "oidc-state"
    except JWTError:
        return False


async def exchange_code(code: str) -> dict:
    discovery = await get_discovery()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.OIDC_REDIRECT_URI,
                "client_id": settings.OIDC_CLIENT_ID,
                "client_secret": settings.OIDC_CLIENT_SECRET,
            },
            headers={"Accept": "application/json"},
        )
        if r.status_code >= 400:
            logger.error("OIDC token exchange failed: %s %s", r.status_code, r.text[:300])
            raise RuntimeError(f"Token exchange failed: {r.status_code}")
        return r.json()


async def fetch_userinfo(access_token: str) -> dict:
    discovery = await get_discovery()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            discovery["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()
