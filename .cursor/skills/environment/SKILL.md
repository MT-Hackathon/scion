---
name: environment
description: "Governs Python/Node.js/Java/Angular environment setup, terminal command execution, and environment variables. Use when setting up environments, executing terminal commands, debugging env var issues, or managing dependencies. DO NOT use for application code patterns or security configuration (see security)."
---

<ANCHORSKILL-ENVIRONMENT>

# Environment Setup

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Script Reference](#script-reference)
- [Script Invocation](#script-invocation)
- [Resources](#resources)
- [Examples: Angular Setup](resources/examples-setup-angular.md)
- [Examples: Universal Setup](resources/examples-setup.md)
- [Examples: Python Setup](resources/examples-setup-python.md)
- [Examples: Terminal](resources/examples-terminal.md)
- [Reference: Environment Variables](resources/reference-env-vars.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Node.js Environment (PRIMARY)

- **Version**: 22+ (LTS) via nvm
- **Package Manager**: npm (not yarn, not pnpm)
- **Framework**: Angular 21 with Angular CLI
- **Activation**: `nvm use 22` before npm/ng commands
- **Project Root**: See Project Information in foundational rule

### Java Environment (Backend)

- **Version**: Java 25 via SDKMAN
- **Build Tool**: Gradle 9.2 with Kotlin DSL
- **Framework**: Spring Boot 4.0.1
- **Activation**: `sdk use java 25` before gradle commands
- **Project Root**: `procurement-api` (relative to workspace)

### Gradle Commands

- **Build**: `./gradlew build`
- **Test**: `./gradlew test`
- **Dev Server**: `./gradlew bootRun` (port 8080, actuator on 8081)
- **Clean**: `./gradlew clean`

### Angular CLI

- **Install**: `npm install -g @angular/cli` (global)
- **Commands**: `ng serve`, `ng build`, `ng test`, `ng generate`
- **Dev Server**: `npm start` or `ng serve` (port 4200)

### Linting

- **Tool**: ESLint with typescript-eslint and angular-eslint
- **Commands**: `npm run lint` (team config), `npm run lint:strict` (personal config if available)
- **Configuration**: See [linter-integration](../linter-integration/SKILL.md) for layered config pattern
- **Personal Config**: `eslint.config.local.js` (gitignored) extends team config with stricter rules

### Anaconda Environment (Universal-API)

- **Conda Env**: `Universal-API`
- **Activation**: `conda activate Universal-API` before any Python commands
- **Interpreter Pinning**: Configure `.vscode/settings.json` with `python.defaultInterpreterPath` pointing at the `Universal-API` conda interpreter
- **Session Reliability**: Re-run `conda activate Universal-API` for each new terminal session
- **Backend**: `uvicorn src.backend.web_api:app --host 0.0.0.0 --port 8000` from repo root
- **Frontend**: `npm run dev -- --host 0.0.0.0 --port 4173` from `src/frontend/`
- **Node.js**: 20 LTS for SvelteKit frontend

### Python Environment (Rule Scripts)

- **Tool**: [uv](https://docs.astral.sh/uv/) for portable script execution
- **Setup**: Run `resources/setup-uv.sh` (Unix) or `resources/setup-uv.ps1` (Windows)
- **Purpose**: Rule automation scripts in `.cursor/rules/*/scripts/`
- **Invocation**: `uv run script.py`
- **Dependencies**: Scripts with deps use PEP 723 inline metadata (auto-installed by uv)

## Script Reference

### setup-uv.sh / setup-uv.ps1
Install uv and configure Python environment for Unix or Windows PowerShell.

### dev-stack.py status
Check local development environment health - running services, ports, containers.

`uv run dev-stack.py status [--format FORMAT] [--check-health] [--ports]`

| Arg | Purpose |
|-----|---------|
| `--format` | Output format: markdown, json, text (default: markdown) |
| `--check-health` | Perform HTTP health checks on services |
| `--ports` | List active ports and listeners |

## Terminal Commands

- **Command Chaining**: Use `&&` for error propagation. NEVER use semicolons `;`.
- **Path Quoting**: Quote paths with spaces: `cd "path with spaces"`.
- **File Operations**: Use `ls`, `find`, `grep`.
- **Path Strategy**: Prefer absolute paths when invoking scripts from nested directories.

## Environment Variables

- **Angular**: Managed via `src/environments/environment.ts`
- **Backend**: `load_dotenv()` in `src/backend/web_api.py`
- **SvelteKit**: Use `$env/dynamic/private` and `$env/dynamic/public`
- **Scripts**: MUST use `python-dotenv` to auto-load credentials from `.env`
- **Security**: Never commit `.env` with real values; use `.env.example`

### Anti-Patterns

- Global npm packages (except Angular CLI)
- Hardcoded paths in scripts
- Skipped nvm activation for Node.js commands
- Running Python scripts without `uv run` (deps may be missing)
- Node.js 24+ versions (use LTS 22.x)
- Semicolons for command chaining
- Unquoted paths containing spaces
- Invoking test runners directly (`npx vitest`, `npx jest`) instead of `npm test --` (bypasses Angular's build pipeline and path alias resolution)
- Trusting empty results from `Get-ChildItem` on Windows — silently returns nothing in junction-point or OneDrive/cloud-synced directories even when files exist; verify with `cmd /c dir "path"` or Python `pathlib.Path.iterdir()` before assuming empty

## Script Invocation

Rule scripts use `uv` for Python execution. This ensures consistent dependencies and avoids environment conflicts.

**Invocation pattern:**
```bash
uv run .cursor/rules/{rule}/scripts/{script}.py
uv run .cursor/skills/{skill}/scripts/{script}.py
```

**Key rules:**
- ALWAYS use `uv run` for rule/skill scripts
- NEVER use bare `python` or `python3` commands
- Scripts auto-load credentials via `python-dotenv` from `.env`
- NEVER read, cat, grep, or source `.env` files directly

## Resources
- [Script Locations](resources/reference-script-locations.md)
- [Project Entry Points](resources/reference-entry-points.md)
- [Tool Selection Checklist](resources/checklist-tool-selection.md)
</ANCHORSKILL-ENVIRONMENT>
