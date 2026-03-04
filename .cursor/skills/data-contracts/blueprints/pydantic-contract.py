# BLUEPRINT: Pydantic contract model and execution entry point
# STRUCTURAL: imports, model definition, execute_entity — keep all
# ILLUSTRATIVE: EntityConfig name, field names, types, literals, endpoint name — replace per contract

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, ValidationError


# STRUCTURAL: model mirrors the Zod schema in zod-contract.ts field-for-field
class EntityConfig(BaseModel):
    """Entity configuration — fields and validation rules must match the Zod schema."""

    name: str = Field(min_length=1)
    url: HttpUrl
    method: Literal["GET", "POST", "PUT", "DELETE"]
    timeout: int = Field(ge=1, le=300)
    auth_type: Literal["none", "api_key", "oauth2"] = "none"
    api_key_ref: str | None = None


# STRUCTURAL: entry point validates config before any execution; rejects with INVALID_CONFIG
def execute_entity(config: dict[str, Any]) -> dict[str, Any]:
    """Execute with validated config. Returns status/data or status/error."""
    try:
        validated = EntityConfig.model_validate(config)
    except ValidationError as err:
        return {
            "status": "error",
            "error": {
                "code": "INVALID_CONFIG",
                "message": str(err),
                "details": err.errors(),
            },
        }

    result = _run(validated)
    return {"status": "success", "data": result}


# ILLUSTRATIVE: replace with real execution logic
def _run(config: EntityConfig) -> dict[str, Any]:
    return {"processed": True, "target": str(config.url)}
