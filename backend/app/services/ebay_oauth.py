"""
Reusable eBay OAuth token helper (refresh + code exchange).
"""
import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.config.ebay_config import (
    get_oauth_endpoint,
    EBAY_OAUTH_CLIENT_ID,
    EBAY_OAUTH_CLIENT_SECRET,
    EBAY_OAUTH_REDIRECT_URI,
    EBAY_REFRESH_TOKEN,
    EBAY_OAUTH_SCOPES,
)

logger = logging.getLogger(__name__)

_token_cache: Dict[str, Any] = {
    "access_token": None,
    "expires_at": 0,
}


def _cache_path() -> Path:
    return Path(__file__).resolve().parents[2] / "cache" / "ebay_oauth_token.json"


def _load_cache() -> None:
    path = _cache_path()
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _token_cache["access_token"] = data.get("access_token")
        _token_cache["expires_at"] = int(data.get("expires_at") or 0)
    except Exception:
        return


def _save_cache(access_token: str, expires_at: int) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "access_token": access_token,
        "expires_at": expires_at,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def _refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    if not EBAY_OAUTH_CLIENT_ID or not EBAY_OAUTH_CLIENT_SECRET:
        raise ValueError("EBAY_OAUTH_CLIENT_ID/EBAY_OAUTH_CLIENT_SECRET not set")

    headers = {
        "Authorization": f"Basic {_basic_auth_header(EBAY_OAUTH_CLIENT_ID, EBAY_OAUTH_CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if EBAY_OAUTH_SCOPES:
        data["scope"] = EBAY_OAUTH_SCOPES

    try:
        response = requests.post(get_oauth_endpoint(), headers=headers, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        msg = f"eBay token refresh failed: {getattr(e.response, 'status_code', 'n/a')} - {detail}"
        logger.error(msg)
        raise ValueError(msg) from e


def get_access_token() -> str:
    """Get a valid access token using refresh token when available."""
    refresh_token = (EBAY_REFRESH_TOKEN or os.getenv("EBAY_REFRESH_TOKEN", "")).strip()

    if not refresh_token:
        # Fallback to manual access token (legacy)
        token = os.getenv("EBAY_ACCESS_TOKEN", "").strip()
        if not token:
            raise ValueError("EBAY_ACCESS_TOKEN not found in environment variables")
        return token

    now = int(time.time())
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    _load_cache()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    token_response = _refresh_access_token(refresh_token)
    access_token = token_response.get("access_token")
    expires_in = int(token_response.get("expires_in") or 0)

    if not access_token or expires_in <= 0:
        raise ValueError("Failed to refresh eBay access token")

    expires_at = int(time.time()) + max(expires_in - 60, 60)
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = expires_at
    _save_cache(access_token, expires_at)
    return access_token


def exchange_authorization_code(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """Exchange authorization code for access + refresh token."""
    if not EBAY_OAUTH_CLIENT_ID or not EBAY_OAUTH_CLIENT_SECRET:
        raise ValueError("EBAY_OAUTH_CLIENT_ID/EBAY_OAUTH_CLIENT_SECRET not set")

    redirect_uri = (redirect_uri or EBAY_OAUTH_REDIRECT_URI or "").strip()
    if not redirect_uri:
        raise ValueError("EBAY_OAUTH_REDIRECT_URI not set")

    headers = {
        "Authorization": f"Basic {_basic_auth_header(EBAY_OAUTH_CLIENT_ID, EBAY_OAUTH_CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(get_oauth_endpoint(), headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json()
