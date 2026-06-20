"""
API key guard for DemandOS write/control endpoints.

When DEMANDOS_API_KEY is set in the environment/config:
  - All protected POST/PATCH endpoints require the header:
    X-DemandOS-API-Key: <key>
  - Returns 401 when the header is absent or wrong.

When DEMANDOS_API_KEY is not set (empty):
  - Guard is disabled — all requests pass (local development mode).

The key is never logged or stored in the database.
"""

from typing import Optional

from fastapi import Header, HTTPException

from app.config import get_settings


async def require_api_key(
    x_demandos_api_key: Optional[str] = Header(default=None),
) -> None:
    """
    FastAPI dependency for write/control endpoint protection.

    Inject with: `Depends(require_api_key)`.
    The return value is None; callers should annotate as `_: None`.
    """
    configured_key = get_settings().demandos_api_key
    if not configured_key:
        return  # guard disabled in dev/test

    if not x_demandos_api_key or x_demandos_api_key != configured_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-DemandOS-API-Key header.",
        )
