# Journey: Error Resilience
**Persona**: Sam — The Daily Practitioner
**Viewport**: All (375px, 768px, 1200px)
**Preconditions**: Dashboard has projects in mixed states. At least one project's repo path has been deleted or is unreachable.
**Routes touched**: `/dashboard`, `/settings/connect`

### Steps

1. **Observe mixed project states** [THIS SPRINT]: Open the dashboard with projects in synced, drifted, and error states.
   - **See**: Each state has a distinct visual indicator — different colors, icons, or badges. The error project is clearly distinguishable from drifted.
   - **Verify**: The error project does NOT prevent other projects from rendering. The rollup cards show correct counts including errors. Synced and drifted projects are fully interactive.

2. **Inspect error project** [THIS SPRINT]: Click the error project's row.
   - **See**: The DrawerPeek opens. The drawer shows a diagnostic section with a human-readable error message (e.g., "Repository path not found: /path/to/deleted/repo").
   - **Verify**: No raw stack trace or JSON blob. The error message suggests a next step (e.g., "Verify the repo path in Settings" or "Reconnect this project"). Pull/Push buttons are disabled or show an explanatory tooltip.

3. **Test full API failure** [THIS SPRINT]: Stop the backend server. Click "Dashboard" in the sidebar (or refresh the page).
   - **See**: The page does not crash. An error banner appears at the top of the content area or a toast notification shows the API is unreachable. The table shows an empty or error state.
   - **Verify**: A "Retry" button is visible. The sidebar navigation still works. The ThemeSwitcher still works. The app shell remains intact — no white screen, no infinite spinner.

4. **Recover from API failure** [THIS SPRINT]: Restart the backend server. Click the "Retry" button.
   - **See**: The dashboard fetches fresh data. The project table populates. The error banner disappears.
   - **Verify**: The data is current, not stale from before the failure.

5. **Form resilience** [THIS SPRINT]: Navigate to `/settings/connect` via the sidebar. Fill in form fields. Before submitting, stop the backend server. Submit the form.
   - **See**: The submit button enters loading state, then an error notification appears.
   - **Verify**: The form retains ALL entered values. Nothing is cleared. The user can restart the server and re-submit without re-entering data.

6. **Theme stability during errors** [CURRENT]: While the app is in any error state, toggle the ThemeSwitcher.
   - **See**: Theme transitions smoothly. Error messages, banners, and badges remain legible in both light and dark themes.
   - **Verify**: Error colors maintain sufficient contrast in dark mode. Interactive elements (Retry button, sidebar links) remain visually distinct.

### Error Variations

- **Timeout vs connection refused**: Verify the app distinguishes between a slow backend (loading spinner with timeout message) and a completely unreachable backend (immediate error). Both should be non-destructive.
- **Partial API failure**: If `GET /api/graft/projects` succeeds but individual status checks fail for some projects, verify: successful projects render normally, failed projects show per-item error state, the dashboard does not show a global error.
