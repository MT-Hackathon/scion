# Reference: Project Entry Points

Quick reference for main project entry points and directory structure.

---

## Environment Activation

```bash
conda activate Universal-API
```

## Backend Entry Point

`src/backend/main.py` is the primary FastAPI entry point.

## Frontend Entry Point

`src/frontend/` contains the SvelteKit application.

- Development: `npm run dev` (from `src/frontend/`)
- Production Build: `npm run build`

---

## Directory Structure

### UI / Frontend (SvelteKit)

| Purpose | Location |
|---------|----------|
| Components | `src/frontend/src/lib/components/` |
| Stores | `src/frontend/src/lib/stores/` |
| Utils | `src/frontend/src/lib/utils/` |
| Routes | `src/frontend/src/routes/` |
| Styles | `src/frontend/src/app.css` |

**Examples:**
- New component: `src/frontend/src/lib/components/DataGrid.svelte`
- New route: `src/frontend/src/routes/settings/+page.svelte`

### Backend (Python/FastAPI)

| Purpose | Location |
|---------|----------|
| API Endpoints | `src/backend/api/` |
| Core Logic | `src/backend/core/` |
| Models | `src/backend/models/` |
| Schemas | `src/backend/schemas/` |

**Examples:**
- New endpoint: `src/backend/api/v1/users.py`
- New schema: `src/backend/schemas/user_schema.py`
