import contextlib
import json
import os
import urllib.error
import urllib.request

REPO = "MT-Hackathon/Universal-API"
API = f"https://api.github.com/repos/{REPO}/issues"
TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not TOKEN:
    raise SystemExit("GITHUB_PERSONAL_ACCESS_TOKEN is required")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "settings-issues-script"
}
LABELS = ["frontend", "feature"]

issues = [
    {
        "title": "Settings API: write to default_app_settings.json and en.json",
        "body": """## Problem\nSettings UI edits must persist to source files for developer-only low-code flow. Need backend API to write updates to `src/frontend/src/lib/config/default_app_settings.json` and `src/frontend/messages/en.json` safely.\n\n## Requirements\n- POST endpoint to accept validated payload for visual settings and copy\n- Writes only to allowed files/paths; reject arbitrary paths\n- Preserve JSON formatting (stable ordering) and validate JSON\n- Authn/authz: restricted to dev/admin users\n- Unit tests for validation and file write\n\n## References\n- default_app_settings.json\n- messages/en.json\n- settingsStore.ts\n\n## Acceptance\n- Endpoint writes changes safely with validation\n- Errors on invalid schema or missing auth\n- JSON remains valid and ordered""",
    },
    {
        "title": "Settings API: rebuild trigger (Apply Changes support)",
        "body": """## Problem\nAfter writing settings/copy to source files, developers need to trigger a rebuild manually from the Settings page.\n\n## Requirements\n- Backend endpoint to trigger rebuild command\n- Command configurable; default: `npm run build` or project-standard\n- Run in repo root `/home/cmb115/projects/Universal-API`\n- Stream/return status; handle failures gracefully\n- Authn/authz restricted to dev/admin\n\n## Acceptance\n- Endpoint kicks off rebuild and returns status\n- Fails safely with clear error if command fails\n- Works on dev machines; production guarded/disabled by config""",
    },
    {
        "title": "Remove CopySettings duplication; migrate copy to en.json",
        "body": """## Problem\nCopy is split between CopySettings (runtime) and Paraglide `en.json` (build-time). With Option E, settings UI will write directly to `en.json`. Need to consolidate to single source of truth.\n\n## Tasks\n- Audit where copy uses CopySettings vs `t()`\n- Move customizable text to `messages/en.json`\n- Remove redundant CopySettings fields and update types\n- Ensure settings UI reads/writes `en.json` via new API\n- Keep visual settings in `default_app_settings.json`\n\n## Acceptance\n- No duplicate copy sources; all strings resolved from `t()` backed by `en.json`\n- Settings UI surfaces the relevant `en.json` entries for editing\n- Types cleaned up accordingly""",
    },
    {
        "title": "Settings UI: Add Apply Changes button (write + rebuild)",
        "body": """## Problem\nAfter editing settings/copy, developers need an explicit \"Apply Changes\" to persist to files and trigger rebuild.\n\n## Requirements\n- Button in settings header or footer\n- On click: call settings write API, then rebuild trigger API\n- Show progress/success/error states; disable during run\n- Guard against unsaved changes; confirm before discard\n\n## Acceptance\n- Apply button successfully writes files and triggers rebuild\n- Clear feedback on success/failure\n- Prevents concurrent double-submit""",
    },
    {
        "title": "Settings Navigation: reorganize sections for growth",
        "body": """## Problem\nCurrent navigation (General/Canvas/Toolbar/Nodes) is cramped. Need structure that matches full surface area.\n\n## Proposed Structure\n- Application: Branding, Behavior\n- Appearance: Typography, Spacing & Radius, Elevation/Shadows, Buttons, Badges\n- Canvas: Background, Grid, Empty State\n- Layout: Header, Toolbar, Sidebar\n- Nodes: Source, Transform, Destination (+ form overrides)\n- Forms: Layout/Validation/Actions\n- Hotkeys: Canvas, Forms, Global\n- Copy & Text: Main page, Dialogs, Toasts, Connection tests, Empty state\n\n## Acceptance\n- Navigation updated to new structure\n- Existing sections still reachable\n- Placeholder/links for new sections""",
    },
    {
        "title": "Settings UI: Typography editors",
        "body": """## Problem\nTypography settings exist in `ThemeTypographySettings` but no UI to edit.\n\n## Tasks\n- Add Typography section\n- Editors for font families, sizes (display/title/subtitle/label/appTitle/nodeTitle), weights, letter spacing\n- Live preview\n- Wire to settings write API (default_app_settings.json)\n\n## Acceptance\n- Typography editable via UI with preview\n- Writes to JSON via API\n- Undo/redo continues to work locally""",
    },
    {
        "title": "Settings UI: Form layout editors",
        "body": """## Problem\n`FormLayoutSettings` defined but not editable; devs must hand-edit JSON.\n\n## Tasks\n- Add Forms section with layout, inputs, validation, actions\n- Controls for gaps, padding, heights, radius token, validation mode/debounce, action alignment\n- Live form preview\n- Persist via settings API\n\n## Acceptance\n- All FormLayoutSettings fields editable\n- Preview updates live\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Settings UI: Hotkey configuration",
        "body": """## Problem\nHotkeySettings exist (canvas/form/dialog/global) but not visible/editable.\n\n## Tasks\n- Hotkeys section listing bindings by context\n- Phase 1: read-only display; Phase 2: editable with conflict detection\n- Persist via settings API\n\n## Acceptance\n- Hotkeys visible in settings UI\n- Editable mode handles conflicts or warns\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Settings UI: Badge color token editors",
        "body": """## Problem\nBadgePalette tokens (blue/green/amber/red/purple) not exposed in UI; needed for dynamic badges (auth type, etc.).\n\n## Tasks\n- Add Badges subsection under Appearance\n- Color pickers for background/border/text per variant, both light/dark\n- Live badge preview\n- Persist via settings API\n\n## Acceptance\n- All badge variants editable\n- Preview reflects light/dark modes\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Settings UI: Canvas empty state styling",
        "body": """## Problem\nEmptyStateTokens (card sizes, typography, grid) are extensive but not editable.\n\n## Tasks\n- Empty State subsection under Canvas\n- Grouped controls for card layout, typography, grid\n- Live preview of empty state\n- Persist via settings API\n\n## Acceptance\n- Key empty state properties editable\n- Preview matches stored values\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Settings UI: Button variant editors",
        "body": """## Problem\nThemeButtonVariants (8 variants) not editable; colors hard to tweak.\n\n## Tasks\n- Buttons subsection under Appearance\n- Variant selector with color pickers for background/hover/active/text/border (+ textHover)\n- Live preview of states\n- Persist via settings API\n\n## Acceptance\n- All 8 variants editable\n- Preview shows states\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Settings UI: Elevation/Shadow editors",
        "body": """## Problem\nThemeElevationSettings for light/dark not editable.\n\n## Tasks\n- Elevation subsection under Appearance\n- Editors for level1/2/3/hover shadows per mode\n- Validate CSS shadow strings; preview card\n- Persist via settings API\n\n## Acceptance\n- Shadows editable and previewed\n- Validation prevents invalid values\n- Writes to default_app_settings.json""",
    },
    {
        "title": "Node settings: add form-specific overrides",
        "body": """## Problem\nForms are contextually tied to node types but settings lack form overrides.\n\n## Tasks\n- Extend Source/Transform/Destination settings with `form` block (e.g., showTestButton, testButtonPosition, validationMode override, autoSaveEnabled)\n- Update types and defaults in default_app_settings.json\n- Add editors in node sections; forms consume overrides\n\n## Acceptance\n- Form overrides defined per node type\n- UI to edit overrides\n- Forms use these settings""",
    },
    {
        "title": "Copy: add main page strings to en.json",
        "body": """## Problem\nMain page has hardcoded strings (Config Sections, Back to Pipeline, Configuration, Open canvas, Go to home page).\n\n## Tasks\n- Add these to `messages/en.json`\n- Replace literals in `src/frontend/src/routes/+page.svelte` and AppHeader with `t()`\n- Expose in settings UI for editing via new en.json write API\n\n## Acceptance\n- All identified strings resolved via t()\n- Settings UI can edit these via en.json updates""",
    },
    {
        "title": "Copy: add toast messages to en.json",
        "body": """## Problem\nToast/status messages (save success/error per node type) are hardcoded.\n\n## Tasks\n- Add toast texts to `messages/en.json` (success/error for source/transform/destination/config)\n- Replace literals in `+page.svelte` with `t()`\n- Expose in settings UI via en.json editing\n\n## Acceptance\n- Toasts resolved via t()\n- Editable via settings UI -> en.json""",
    },
    {
        "title": "Copy: add connection test messages to en.json",
        "body": """## Problem\nConnection test status strings hardcoded.\n\n## Tasks\n- Add testing/success/unable-to-verify/failure strings to `messages/en.json`\n- Replace literals in `+page.svelte` with `t()`\n- Editable via settings UI\n\n## Acceptance\n- Connection test messages resolved via t()\n- Editable through settings page writes to en.json""",
    },
    {
        "title": "Copy: add missing dialog copy to en.json",
        "body": """## Problem\nDialog copy partly in i18n, partly hardcoded; not editable through settings.\n\n## Tasks\n- Ensure draft recovery, save pipeline, pipeline library dialog strings complete in `messages/en.json`\n- Replace any remaining literals\n- Expose these keys in settings UI for editing via en.json write API\n\n## Acceptance\n- All dialog copy resolved via t()\n- Editable through settings page""",
    },
    {
        "title": "Copy: canvas empty state text editors",
        "body": """## Problem\nCanvas empty state text in i18n but not editable in settings UI.\n\n## Tasks\n- Add empty state copy keys to `messages/en.json` if missing (pill, heading, body, intent labels/descriptions)\n- Expose in settings UI alongside styling controls\n- Use t() in Canvas component\n\n## Acceptance\n- Empty state copy editable via settings page\n- Canvas uses t() for these strings""",
    },
    {
        "title": "Docs: CSS override pattern for context styling",
        "body": """## Problem\nContext-specific styling uses CSS vars + classes but not documented, leading to inconsistent patterns.\n\n## Tasks\n- Document when to use settings vs CSS class overrides\n- Define naming convention (.node-form-input, .source-node-input, etc.)\n- Show variable override pattern examples\n- Add doc to .cursor/context or project docs\n\n## Acceptance\n- Documentation exists with examples and guidance\n- Linked from contributing/design docs""",
    },
    {
        "title": "Refactor: settings section renderer pattern",
        "body": """## Problem\nSettings page has large manual section blocks; hard to extend.\n\n## Tasks\n- Create registry-driven section renderer (field configs -> components)\n- Extract field metadata to config file (e.g., settingsRegistry.ts)\n- Replace long chain of if/else with renderer\n- Ensure parity with existing functionality\n\n## Acceptance\n- Renderer covers existing sections\n- Adding new section requires registry entry only\n- Page size reduced and maintainable""",
    },
]

for issue in issues:
    payload = {"title": issue["title"], "body": issue["body"], "labels": LABELS}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode()
            print(f"Created: {issue['title']} (status {resp.status})")
    except urllib.error.HTTPError as e:
        print(f"Failed: {issue['title']} -> {e.code} {e.reason}")
        with contextlib.suppress(Exception):
            print(e.read().decode())
        raise
