# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Verify implementation completeness for a Feature Card.

Scans the codebase to assess which layers (backend, frontend, tests) exist
for a given feature, based on known component mappings.
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Feature Card to codebase mapping
FEATURE_MAP: dict[str, dict] = {
    "F-01": {
        "name": "Procurement Request Intake",
        "backend_patterns": ["intake", "IntakeDomain", "IntakeController"],
        "frontend_patterns": ["new-request", "intake", "cost-calculator", "attachment-upload"],
        "service_patterns": ["IntakeService", "intake.service", "DraftsListService", "drafts-list.service"],
        "test_patterns": ["intake", "new-request", "cost-calculator"],
        "route": "/requests/new",
    },
    "F-02": {
        "name": "APO Refinement",
        "backend_patterns": ["Refinement", "RefinementDomain", "refine"],
        "frontend_patterns": ["refinement-form", "refinement", "base-section", "budget-section",
                              "commodity-section", "financials-section", "sourcing-section",
                              "contract-terms-section", "compliance-section", "certification-section",
                              "legal-review-section", "procurement-method-section"],
        "service_patterns": ["RefinementService", "refinement.service", "FormModeService",
                              "RefinementPermissionsService", "RefinementFormBuilderService"],
        "test_patterns": ["refinement", "refine"],
        "route": "/requests/:id/refine",
    },
    "F-03": {
        "name": "Parallel Approval Gates",
        "backend_patterns": ["Approval", "ApprovalsController", "ApprovalsService"],
        "frontend_patterns": ["approver-dashboard", "apo-queue", "more-info-dialog", "deny-dialog"],
        "service_patterns": ["ApproverDashboardService", "approver-dashboard.service"],
        "test_patterns": ["approval", "approver-dashboard"],
        "route": "/approvals",
    },
    "F-04": {
        "name": "Rules-Driven Business Logic",
        "backend_patterns": ["Rules", "RulesService", "RulesController", "ConditionNode"],
        "frontend_patterns": ["rules-list", "rule-editor", "rule-simulator",
                              "condition-builder", "approval-path-builder"],
        "service_patterns": ["RulesService", "rules.service", "RuleEvaluationService",
                              "RuleSimulationService", "WorkflowGeneratorService"],
        "test_patterns": ["rules", "rule-editor", "condition-builder"],
        "route": "/rules",
    },
    "F-05": {
        "name": "Agency Sovereignty",
        "backend_patterns": ["purchasingAgencyId", "AgencyResolver", "IdentityService"],
        "frontend_patterns": ["identity-validation"],
        "service_patterns": ["IdentityValidationService", "identity-validation.service"],
        "test_patterns": ["agency", "sovereignty", "identity-validation"],
        "route": None,
    },
    "F-06": {
        "name": "Delegated Authority Management",
        "backend_patterns": ["DelegatedAuthority", "threshold", "RoutingService"],
        "frontend_patterns": ["threshold-alert"],
        "service_patterns": ["ThresholdService", "threshold.service"],
        "test_patterns": ["threshold", "delegated-authority", "routing"],
        "route": None,
    },
    "F-07": {
        "name": "Role-Based Access Control",
        "backend_patterns": ["UserRoles", "UserRoleService", "SecurityConfig"],
        "frontend_patterns": ["role-selector", "side-navigation", "permission"],
        "service_patterns": ["ActiveRoleService", "active-role.service", "PermissionService",
                              "permission.service", "RoleService", "role.service"],
        "test_patterns": ["role", "permission", "auth"],
        "route": None,
    },
    "F-08": {
        "name": "Approval Path Visualization",
        "backend_patterns": ["ApprovalPath", "ApprovalPathDomain"],
        "frontend_patterns": ["approval-path", "workflow-progress",
                              "approval-path-visualization"],
        "service_patterns": ["ApprovalPathService", "approval-path.service"],
        "test_patterns": ["approval-path", "workflow-progress"],
        "route": "/requests/:id/approval-path",
    },
    "F-09": {
        "name": "Queue Management",
        "backend_patterns": ["Assignment", "AssignmentsService", "AssignmentsController"],
        "frontend_patterns": ["assignments-dashboard", "reassign-dialog", "apo-queue"],
        "service_patterns": ["AssignmentsService", "assignments.service"],
        "test_patterns": ["assignment", "queue", "reassign"],
        "route": "/assignments",
    },
    "F-10": {
        "name": "Entity Configuration",
        "backend_patterns": ["Agency", "Category", "Vendor", "EntityConfig"],
        "frontend_patterns": ["entity-config", "agency-list", "agency-form",
                              "category-list", "category-form", "vendor-list", "vendor-form"],
        "service_patterns": ["AgencyService", "agency.service", "CategoryService",
                              "category.service", "VendorService", "vendor.service"],
        "test_patterns": ["entity-config", "agency", "category", "vendor"],
        "route": "/entity-config",
    },
    "F-11": {
        "name": "Delegation Administration",
        "backend_patterns": ["Delegation", "DelegationService", "DelegationController"],
        "frontend_patterns": ["delegation-admin-listing", "delegation-admin-edit"],
        "service_patterns": ["DelegationService", "delegation.service"],
        "test_patterns": ["delegation"],
        "route": "/delegation",
    },
    "F-12": {
        "name": "Attachment Management",
        "backend_patterns": ["Attachment", "AttachmentController", "AttachmentService"],
        "frontend_patterns": ["attachment-upload"],
        "service_patterns": ["AttachmentService", "attachment.service"],
        "test_patterns": ["attachment"],
        "route": None,
    },
    "F-13": {
        "name": "Audit Trail",
        "backend_patterns": ["Audit", "StatusHistory", "REQUEST_STATUS_HISTORY"],
        "frontend_patterns": [],
        "service_patterns": [],
        "test_patterns": ["audit", "status-history"],
        "route": None,
    },
    "F-14": {
        "name": "Display Name Architecture",
        "backend_patterns": ["DisplayNameRegistry", "displayName"],
        "frontend_patterns": ["display-name"],
        "service_patterns": ["DisplayNameRegistryService", "display-name-registry.service"],
        "test_patterns": ["display-name", "humanize"],
        "route": None,
    },
}


@dataclass
class LayerResult:
    """Result for a single layer check."""
    name: str
    patterns_checked: int = 0
    patterns_found: int = 0
    files: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def search_pattern(pattern: str, search_dir: str) -> list[str]:
    """Search for a pattern in the codebase using ripgrep or grep fallback."""
    for cmd in [
        ["rg", "-l", "--no-heading", pattern, search_dir],
        ["grep", "-rl", "--include=*.ts", "--include=*.java", "--include=*.html", pattern, search_dir],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            if result.returncode == 1:
                return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return []


def check_layer(patterns: list[str], search_dir: str, layer_name: str) -> LayerResult:
    """Check if patterns exist in a directory."""
    result = LayerResult(name=layer_name, patterns_checked=len(patterns))
    for pattern in patterns:
        files = search_pattern(pattern, search_dir)
        if files:
            result.patterns_found += 1
            result.files.extend(files)
        else:
            result.missing.append(pattern)
    result.files = sorted(set(result.files))
    return result


def verify_feature(feature_id: str, workspace: Path, verbose: bool = False) -> None:
    """Verify implementation completeness for a feature."""
    feature_id = feature_id.upper()
    if feature_id not in FEATURE_MAP:
        print(f"ERROR: Unknown feature ID '{feature_id}'. Valid IDs: {', '.join(sorted(FEATURE_MAP.keys()))}")
        sys.exit(1)

    config = FEATURE_MAP[feature_id]
    print(f"\n{'=' * 60}")
    print(f"  {feature_id}: {config['name']}")
    print(f"{'=' * 60}")

    if config.get("route"):
        print(f"  Route: {config['route']}")
    print()

    # Resolve project roots — workspace may be procurement-web itself or the parent
    api_candidates = [
        workspace / "procurement-api" / "src",
        workspace.parent / "procurement-api" / "src",
    ]
    web_candidates = [
        workspace / "src",  # workspace IS procurement-web
        workspace / "procurement-web" / "src",
    ]

    api_dir = next((d for d in api_candidates if d.exists()), None)
    web_dir = next((d for d in web_candidates if d.exists()), None)

    layers = []

    # Backend check
    if api_dir:
        backend = check_layer(config["backend_patterns"], str(api_dir), "Backend")
        layers.append(backend)
    else:
        print("  NOTE: procurement-api not found. Skipping backend checks.")

    # Frontend components
    if web_dir:
        frontend = check_layer(config["frontend_patterns"], str(web_dir / "app"), "Frontend Components")
        layers.append(frontend)

        # Frontend services
        services = check_layer(config["service_patterns"], str(web_dir / "app"), "Frontend Services")
        layers.append(services)

        # Tests
        tests = check_layer(config["test_patterns"], str(web_dir), "Tests")
        layers.append(tests)
    else:
        print("  NOTE: procurement-web/src not found.")

    # Summary
    print("  Layer Summary")
    print("  " + "-" * 50)
    total_found = 0
    total_checked = 0
    for layer in layers:
        total_found += layer.patterns_found
        total_checked += layer.patterns_checked
        pct = (layer.patterns_found / layer.patterns_checked * 100) if layer.patterns_checked > 0 else 0
        status = "PASS" if pct >= 80 else ("PARTIAL" if pct >= 40 else "GAP")
        icon = {"PASS": "+", "PARTIAL": "~", "GAP": "!"}[status]
        print(f"  [{icon}] {layer.name}: {layer.patterns_found}/{layer.patterns_checked} patterns found ({pct:.0f}%) [{status}]")

    overall_pct = (total_found / total_checked * 100) if total_checked > 0 else 0
    print()
    print(f"  Overall: {total_found}/{total_checked} ({overall_pct:.0f}%)")
    print()

    if verbose:
        for layer in layers:
            if layer.files:
                print(f"  {layer.name} Files:")
                for f in layer.files[:20]:
                    print(f"    {f}")
                if len(layer.files) > 20:
                    print(f"    ... and {len(layer.files) - 20} more")
                print()
            if layer.missing:
                print(f"  {layer.name} Missing Patterns:")
                for m in layer.missing:
                    print(f"    - {m}")
                print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify implementation completeness for a Feature Card"
    )
    parser.add_argument("feature_id", help="Feature Card ID (e.g., F-01, F-03)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed file matches")
    parser.add_argument("--all", "-a", action="store_true", help="Check all features")
    args = parser.parse_args()

    workspace = Path.cwd()

    if args.all:
        for fid in sorted(FEATURE_MAP.keys()):
            verify_feature(fid, workspace, args.verbose)
    else:
        verify_feature(args.feature_id, workspace, args.verbose)


if __name__ == "__main__":
    main()
