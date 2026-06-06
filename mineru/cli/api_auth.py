# Copyright (c) Opendatalab. All rights reserved.
import secrets
from typing import Optional

from fastapi import HTTPException, Request

AUTHORIZATION_HEADER = "Authorization"
API_KEY_HEADER = "X-API-Key"
MINERU_API_KEY_ENV = "MINERU_API_KEY"
UNAUTHORIZED_DETAIL = "Invalid or missing API key"


def build_api_auth_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {AUTHORIZATION_HEADER: f"Bearer {api_key}"}


def resolve_configured_api_key(cli_api_key: str | None) -> str | None:
    if cli_api_key:
        normalized_api_key = cli_api_key.strip()
        if normalized_api_key:
            return normalized_api_key
    return None


def extract_api_key_from_request(request: Request) -> Optional[str]:
    authorization = request.headers.get(AUTHORIZATION_HEADER)
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()

    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        return api_key.strip()
    return None


def validate_api_key_request(request: Request) -> None:
    configured_api_key = resolve_configured_api_key(
        getattr(request.app.state, "api_key", None)
    )
    if not configured_api_key:
        return

    provided_api_key = extract_api_key_from_request(request)
    if provided_api_key and secrets.compare_digest(provided_api_key, configured_api_key):
        return

    raise HTTPException(
        status_code=401,
        detail=UNAUTHORIZED_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )
