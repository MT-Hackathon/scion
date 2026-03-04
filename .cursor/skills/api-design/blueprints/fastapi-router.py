# BLUEPRINT | FastAPI Router with Pydantic Models and Error Handling
# STRUCTURAL: router prefix/tags, _problem() helper, request/response model classes,
#             explicit mapping functions, GET with Query params, POST with body model,
#             tiered exception handling raising HTTPException from domain errors
# ILLUSTRATIVE: route paths ("/status", "/operation"), model names, field names,
#               error title strings, specific exception types, domain call signatures

"""<domain> API endpoints."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from <domain>.errors import ConfigError, DomainError        # ILLUSTRATIVE: error hierarchy
from <domain>.models import DomainResult                    # ILLUSTRATIVE: internal model
from <domain>.workflows import run_operation                # ILLUSTRATIVE: domain entrypoint

router = APIRouter(prefix="/api/<domain>", tags=["<domain>"])  # ILLUSTRATIVE: prefix/tags


# STRUCTURAL: single RFC 7807-style error helper — never construct HTTPException inline
def _problem(status: int | HTTPStatus, title: str, detail: str) -> HTTPException:
    code = int(status)
    return HTTPException(
        status_code=code,
        detail={"title": title, "detail": detail, "status": code},
    )


# --- Request models ---

class OperationRequest(BaseModel):             # ILLUSTRATIVE: class name
    target_path: str = Field(..., min_length=1)  # STRUCTURAL: Field() on every validated input
    dry_run: bool = False                        # STRUCTURAL: bool flags default False


# --- Response models ---

class OperationResponse(BaseModel):            # ILLUSTRATIVE: class name
    items_written: int                         # ILLUSTRATIVE: field names
    items_skipped: int
    committed: bool


# STRUCTURAL: explicit mapping function — never construct response model inline inside endpoint
def to_operation_response(result: DomainResult) -> OperationResponse:  # ILLUSTRATIVE: names
    return OperationResponse(
        items_written=result.items_written,
        items_skipped=result.items_skipped,
        committed=result.committed,
    )


# --- Endpoints ---

# STRUCTURAL: GET with query params — use Query() for every query parameter
@router.get("/status", response_model=OperationResponse)   # ILLUSTRATIVE: path
def get_status(target_path: str = Query(...)):             # ILLUSTRATIVE: param name
    """<One-line operation description>."""
    if not target_path.strip():                            # STRUCTURAL: guard clause before domain call
        raise _problem(HTTPStatus.BAD_REQUEST, "Validation", "target_path must not be empty")

    try:
        result = run_operation(target_path)                # ILLUSTRATIVE: domain call
    except ConfigError as exc:
        raise _problem(HTTPStatus.BAD_REQUEST, "Configuration", str(exc)) from exc
    except DomainError as exc:
        raise _problem(HTTPStatus.INTERNAL_SERVER_ERROR, "InternalError", str(exc)) from exc

    return to_operation_response(result)


# STRUCTURAL: POST with body model — annotate param as `body: RequestModel`, not kwargs
@router.post("/operation", response_model=OperationResponse)  # ILLUSTRATIVE: path
def post_operation(body: OperationRequest):                   # ILLUSTRATIVE: model name
    """<One-line operation description>."""
    try:
        result = run_operation(body.target_path, dry_run=body.dry_run)  # ILLUSTRATIVE
    except ConfigError as exc:
        raise _problem(HTTPStatus.BAD_REQUEST, "Configuration", str(exc)) from exc
    except DomainError as exc:
        raise _problem(HTTPStatus.INTERNAL_SERVER_ERROR, "InternalError", str(exc)) from exc

    return to_operation_response(result)
