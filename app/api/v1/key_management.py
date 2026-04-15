from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field

from storage.repositories.api_keys_repository import TIER_QUOTAS, create_api_key, list_api_keys, revoke_api_key

key_mgmt_router = APIRouter(prefix="/api-keys", tags=["internal-key-management"])

_VALID_TIERS = set(TIER_QUOTAS.keys())


class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(..., min_length=1, max_length=200)
    tier: str


class CreateKeyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key_id: str
    raw_key: str
    label: str
    tier: str
    quota_per_day: int


class KeyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key_id: str
    label: str
    tier: str
    quota_per_day: int
    requests_today: int
    quota_reset_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class KeyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[KeyItem]


@key_mgmt_router.post("", response_model=CreateKeyResponse, status_code=201)
def create_key(body: CreateKeyRequest):
    """Create a new API key. The raw_key is returned only once."""
    if body.tier not in _VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {sorted(_VALID_TIERS)}")
    return create_api_key(label=body.label, tier=body.tier)


@key_mgmt_router.get("", response_model=KeyListResponse)
def get_keys():
    """List all API keys. key_hash is never returned."""
    return {"items": list_api_keys()}


@key_mgmt_router.delete("/{key_id}", status_code=204, response_model=None)
def delete_key(key_id: str = Path(...)):
    """Revoke an API key by setting is_active = false."""
    revoke_api_key(key_id)
