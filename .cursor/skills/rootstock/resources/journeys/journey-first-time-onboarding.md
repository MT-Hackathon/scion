# Journey: First-Time Onboarding
**Persona**: Alex — The New Contributor
**Viewport**: All (375px, 768px, 1200px)
**Preconditions**: App is running. No projects have been connected (fresh state).
**Routes touched**: `/dashboard`, `/settings/connect`

### Steps

1. **Open the application** [CURRENT]: Launch the Tauri desktop app (`cargo tauri dev` or the installed binary). In frontend-only dev mode, navigate to `http://localhost:5173`.
   - **See**: The app loads. The sidebar contains navigation links. The main content area renders the default page.
   - **Verify**: No console errors. The theme matches system preference (light or dark). On mobile (375px), the sidebar is hidden and a hamburger menu is visible in the top bar.

2. **Navigate to Dashboard** [CURRENT]: Click the "Dashboard" link in the sidebar. On mobile, tap the hamburger menu first, then tap "Dashboard."
   - **See**: The dashboard page loads at `/dashboard`. Because no projects are connected, the page shows an empty state.
   - **Verify**: The empty state includes a clear call-to-action — a "Connect Project" button or link. The table area shows an empty state message, not a blank void.

3. **Click "Connect Project"** [THIS SPRINT]: Click the primary action button/link labeled "Connect Project" in the empty state or header.
   - **See**: The URL changes to `/settings/connect`. The FormPage layout renders a connection form.
   - **Verify**: The page title is visible. The form contains labeled fields: Project Name, Local Repo Path, Rootstock Repo Path, and Contributor Name. On mobile, the form fields stack vertically with full-width inputs.

4. **Trigger validation errors** [THIS SPRINT]: Without filling any fields, click the submit button (labeled "Connect" or similar).
   - **See**: Inline error messages appear below each required field. The form does not submit. The page does not navigate away.
   - **Verify**: Each empty required field shows a specific error message (not a generic "required"). The submit button is not in a loading state. Focus moves to the first error field or an error summary.

5. **Enter invalid path** [THIS SPRINT]: Fill "Local Repo Path" with a clearly invalid value (e.g., `not-a-real-path`), fill other required fields with valid data, and click submit.
   - **See**: The form submits (client validation passes for format). The API returns an error. An error notification or inline error appears.
   - **Verify**: The error message is human-readable (not a raw stack trace). The form retains all entered values — the user does not have to re-type anything.

6. **Submit valid form** [THIS SPRINT]: Correct the path to a valid local repo path and click submit.
   - **See**: The submit button shows a loading spinner. On success, the app navigates back to `/dashboard`.
   - **Verify**: A success toast notification appears (e.g., "Project connected"). The toast auto-dismisses after a few seconds.

7. **Verify new project on Dashboard** [THIS SPRINT]: The dashboard now shows one project in the table.
   - **See**: A new row with the project name entered in Step 6. The status column shows "drifted" or "new" (since no pull has been performed).
   - **Verify**: The rollup summary cards (if present) update to show 1 total project, 1 drifted.

8. **Open project drawer** [CURRENT]: Click the project row in the table.
   - **See**: The DrawerPeek slides in from the right with project details and action buttons.
   - **Verify**: The drawer shows the project name, status, last sync timestamps (or "Never"), and action buttons (Pull, Push, Check Status).

9. **Perform first pull** [THIS SPRINT]: Click the "Pull" button in the drawer.
   - **See**: The button enters a loading state. On success, the status updates to "synced."
   - **Verify**: The table row behind the drawer also updates. A success notification appears.

10. **Toggle dark mode** [CURRENT]: Click the ThemeSwitcher in the top bar.
    - **See**: The entire app transitions to the alternate theme.
    - **Verify**: All elements remain legible. The project table, drawer, and status indicators maintain visual distinction in both themes.

### Error Variations

- **Already-connected project**: Submit the connect form with a repo path that is already connected. Verify: clear error message, not a duplicate entry in the registry.
- **API unreachable during connect**: Submit the form while the backend is down. Verify: error notification appears, form retains entered values, no white screen.
- **Drawer close and reopen**: Close the drawer (click overlay or X), then click the same row again. Verify: drawer reopens with correct data.
