# BLUEPRINT | Pydantic/Dataclass DTO Contracts
# STRUCTURAL: StrEnum for fixed protocol values, frozen dataclasses with slots=True,
#             T | None union syntax for optional fields, Path for filesystem refs,
#             typed dict[K, V] (no dict[str, Any]), nested composition over flat mega-models,
#             docstring on every model
# ILLUSTRATIVE: class names, field names, enum values, module docstring

"""<domain> domain model contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


# STRUCTURAL: StrEnum for fixed protocol-level values only
#             DO NOT use for configurable/tenant-specific values — those are str with description
class ActionType(StrEnum):    # ILLUSTRATIVE: name and members
    IGNORE = "IGNORE"
    SKIP = "SKIP"
    COPY = "COPY"


# STRUCTURAL: frozen=True + slots=True on all immutable domain models
@dataclass(frozen=True, slots=True)
class ItemAction:             # ILLUSTRATIVE: name
    """Planned action for a single item."""   # STRUCTURAL: docstring on every model
    action: ActionType
    relative_path: str
    content: str | None       # STRUCTURAL: optional → T | None, not Optional[T]


# STRUCTURAL: compose from smaller frozen dataclasses — avoid flat mega-models
@dataclass(frozen=True, slots=True)
class OperationResult:        # ILLUSTRATIVE: name
    """Outcome of an operation."""
    items_written: int
    items_skipped: int
    committed: bool
    commit_message: str | None   # STRUCTURAL: nullable; caller supplies None explicitly


# STRUCTURAL: use Path for filesystem references — not bare str
@dataclass(frozen=True, slots=True)
class ProjectConfig:          # ILLUSTRATIVE: name
    """Per-project configuration contract."""
    project_id: str
    project_name: str
    local_path: Path                       # STRUCTURAL: Path, not str
    template_values: dict[str, str]        # STRUCTURAL: typed dicts, not dict[str, Any]
    optional_remote: str | None = None     # STRUCTURAL: optional fields with defaults trail required fields
