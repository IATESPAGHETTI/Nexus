"""Thin, bounded HTTP client for production/'s mutating admin endpoints.

Deliberately separate from `mcp/production_client.py` (dependency isolation,
same principle as every other top-level folder) even though the shape is
almost identical -- `mcp/`'s client is read-only-tool-bound and lives in a
different venv; this one is guardrails-only and is the ONLY code in the whole
system with real execution capability. Every call has a fixed timeout and
raises a small typed error instead of leaking a raw exception.
"""

from __future__ import annotations

import httpx

from config import HTTP_TIMEOUT_SECONDS, PRODUCTION_BASE_URL


class ProductionUnavailableError(Exception):
    pass


def post(path: str, json: dict | None = None) -> dict:
    url = f"{PRODUCTION_BASE_URL}{path}"
    try:
        response = httpx.post(url, json=json or {}, timeout=HTTP_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise ProductionUnavailableError(f"timeout calling {path}") from exc
    except httpx.RequestError as exc:
        raise ProductionUnavailableError(f"could not reach {path}: {exc}") from exc

    if response.status_code >= 400:
        raise ProductionUnavailableError(f"{path} returned HTTP {response.status_code}: {response.text}")
    return response.json()


def get(path: str) -> dict:
    url = f"{PRODUCTION_BASE_URL}{path}"
    try:
        response = httpx.get(url, timeout=HTTP_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise ProductionUnavailableError(f"timeout calling {path}") from exc
    except httpx.RequestError as exc:
        raise ProductionUnavailableError(f"could not reach {path}: {exc}") from exc

    if response.status_code >= 400:
        raise ProductionUnavailableError(f"{path} returned HTTP {response.status_code}")
    return response.json()
