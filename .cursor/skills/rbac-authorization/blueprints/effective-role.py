# BLUEPRINT: Inheritance A — effective_role and authorize_action
# STRUCTURAL: resolution order (direct override → direct baseline → nearest ancestor → None)
# ILLUSTRATIVE: DB function names (get_direct_membership, get_ancestor_teams)

from __future__ import annotations

ROLE_ACTIONS: dict[str, list[str]] = {
    "Viewer":   ["view", "audit"],
    "Executor": ["view", "audit", "execute"],
    "Editor":   ["view", "audit", "execute", "edit", "share"],
    "Admin":    ["view", "audit", "execute", "edit", "share", "delete", "manage_team"],
}


def effective_role(user_id: str, team_id: str) -> str | None:
    """Return the effective role for user on team via Inheritance A.

    Resolution: direct override > direct baseline > nearest-ancestor role > None.
    Never trust a client-supplied team_id — always resolve from the server's graph.
    """
    # 1. Direct membership always wins.
    direct = get_direct_membership(user_id, team_id)  # ILLUSTRATIVE
    if direct:
        return direct.role_override or direct.role_baseline

    # 2. Walk ancestors nearest-first; stop at first match.
    for ancestor in get_ancestor_teams(team_id):  # ILLUSTRATIVE: cycle-safe traversal
        membership = get_direct_membership(user_id, ancestor.id)  # ILLUSTRATIVE
        if membership:
            return membership.role_override or membership.role_baseline

    return None  # No access anywhere in the hierarchy.


def authorize_action(user_id: str, resource_team_id: str, action: str) -> bool:
    """Return True iff user's effective role permits the requested action."""
    role = effective_role(user_id, resource_team_id)
    if not role:
        return False
    return action in ROLE_ACTIONS.get(role, [])
