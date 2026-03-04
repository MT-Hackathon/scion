# BLUEPRINT: error-hierarchy
# STRUCTURAL: domain root, category subclasses, contextual subclasses with typed fields
# ILLUSTRATIVE: class names → your domain; messages → your invariant language

"""Domain error hierarchy.

Pattern:
  1. Domain root inherits Exception — all domain errors share a common catch point.
  2. Simple typed subclasses for category-level catches (no extra context needed).
  3. Contextual subclasses carry structured fields for logging and recovery.
  4. Messages are actionable — state what failed and what to do next.
"""

from __future__ import annotations


# --- Domain root ---------------------------------------------------------

class GraftError(Exception):
    """Base for all graft domain errors. Never raised directly."""


# --- Category errors (simple subclasses) ---------------------------------

class ConfigError(GraftError):
    """Configuration loading or validation failure."""


class PolicyError(GraftError):
    """Policy classification or invariant violation."""


class GitError(GraftError):
    """Git command execution error."""


# --- Contextual errors (structured fields) --------------------------------

class UnclassifiedFilesError(PolicyError):
    """Files without lifecycle classification (fail-closed invariant)."""

    def __init__(self, paths: list[str]) -> None:
        self.paths = paths                        # STRUCTURAL: retain typed context for recovery
        super().__init__(
            f"Unclassified file(s) must not sync: {', '.join(paths)}. "
            "Add each to graft-policy.json before retrying."
        )


class TemplateError(GraftError):
    """Unresolved template placeholders."""

    def __init__(self, unresolved: list[str]) -> None:
        self.unresolved = unresolved              # STRUCTURAL: retain typed context for recovery
        super().__init__(
            f"Unresolved placeholders: {', '.join(sorted(set(unresolved)))}"
        )
