# Reference Implementations

Production source files that the FastAPI blueprints were extracted from. Read these when the blueprints leave a pattern ambiguous or when you need full context.

## FastAPI Router

**File**: `app/backend/src/routers/graft_router.py`

Demonstrates:
- `_problem()` helper producing RFC 7807 Problem Details dicts
- Pydantic request and response models with `Field()` validation
- Explicit mapping functions (domain model → response model) keeping endpoints thin
- GET endpoint with `Query()` parameters and guard clause validation
- POST endpoint with body model and tiered exception hierarchy (`ConfigError → 400`, `GraftError → 500`)
- Composite response models (e.g., `StatusResponse` nesting `InboundDriftResponse` + `OutboundDriftResponse`)

## Domain Model Contracts

**File**: `app/backend/src/graft/models.py`

Demonstrates:
- `StrEnum` for fixed protocol-level action values (`PullActionType`)
- `@dataclass(frozen=True, slots=True)` on every domain model
- `Path` / `PurePosixPath` for filesystem references (not `str`)
- `T | None` union syntax for optional fields
- Nested composition: `StatusResult` references `InboundDrift` + `OutboundDrift` + `PullDelta`
- Docstrings on every model class
