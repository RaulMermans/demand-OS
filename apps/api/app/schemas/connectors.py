"""
Connector prep schemas (Sprint 13).

Real connectors (Shopify, WooCommerce) are disabled by default.
These schemas describe the config shape for future enablement only.
No credentials are stored.
"""

from typing import Any, Optional
from pydantic import BaseModel


class ConnectorStatus(BaseModel):
    connector_id: str
    name: str
    description: str
    status: str                    # disabled / config_ready / active
    enabled: bool
    requires_credentials: list[str]
    capabilities: list[str]
    note: str


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
    total: int


class ConnectorConfigValidateRequest(BaseModel):
    connector_id: str
    config: dict[str, Any]


class ConnectorConfigValidateResponse(BaseModel):
    connector_id: str
    is_valid: bool
    missing_fields: list[str]
    unknown_fields: list[str]
    notes: list[str]
    warning: str = "Config validation only — no credentials are stored."


class ConnectorDryRunRequest(BaseModel):
    connector_id: str
    config: dict[str, Any]


class ConnectorDryRunResponse(BaseModel):
    connector_id: str
    status: str                    # always "disabled" for real connectors
    message: str
    would_fetch: list[str]
    estimated_record_types: list[str]
    warning: str = "Dry-run only — no live API calls were made."
