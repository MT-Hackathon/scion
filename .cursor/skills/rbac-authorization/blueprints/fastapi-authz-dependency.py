# BLUEPRINT: FastAPI authorization dependency
# STRUCTURAL: require_permission factory returning a FastAPI Depends object
# ILLUSTRATIVE: action strings ("view", "edit"), model names (User, Pipeline)

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Depends, HTTPException

from .auth import get_current_user   # ILLUSTRATIVE: replace with your auth dependency
from .models import User             # ILLUSTRATIVE: replace with your User model import
from .rbac import authorize_action   # STRUCTURAL: must delegate to centralized rbac module


def require_permission(action: str) -> Callable:
    """Return a FastAPI dependency that checks the given action against the resource's team.

    Usage:
        @router.get("/pipelines/{pipeline_id}")
        async def get_pipeline(
            pipeline_id: str,
            authorize: Callable = require_permission("view"),
        ):
            pipeline = db.get_pipeline(pipeline_id)
            if pipeline is None:
                raise HTTPException(status_code=404)
            await authorize(pipeline.owned_by_team_id)
            return pipeline
    """
    async def _check_permission(
        current_user: User = Depends(get_current_user),
    ) -> Callable[[str], Awaitable[None]]:
        async def _authorize(resource_team_id: str) -> None:
            if not authorize_action(current_user.id, resource_team_id, action):
                raise HTTPException(status_code=403, detail="Forbidden")

        return _authorize

    return Depends(_check_permission)
