"""Thin, bounded HTTP client for the simulated production service (Phase 2).

Every call has a fixed timeout and raises a small typed error the tool layer can
turn into a structured, non-crashing tool result instead of letting exceptions
leak raw stack traces (and potentially internals) back to a caller.
"""

from __future__ import annotations

import httpx

from config import HTTP_TIMEOUT_SECONDS, PRODUCTION_BASE_URL


class ProductionUnavailableError(Exception):
    pass


class ProductionNotFoundError(Exception):
    pass


def get(path: str, params: dict | None = None) -> dict:
    url = f"{PRODUCTION_BASE_URL}{path}"
    try:
        response = httpx.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise ProductionUnavailableError(f"timeout calling {path}") from exc
    except httpx.RequestError as exc:
        raise ProductionUnavailableError(f"could not reach {path}: {exc}") from exc

    if response.status_code == 404:
        raise ProductionNotFoundError(f"{path} returned 404")
    if response.status_code >= 400:
        raise ProductionUnavailableError(
            f"{path} returned HTTP {response.status_code}"
        )
    return response.json()
