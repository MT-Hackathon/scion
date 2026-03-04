# Journey: Daily Sync Check
**Persona**: Sam — The Daily Practitioner
**Viewport**: All (375px, 768px, 1200px)
**Preconditions**: Dashboard has 3+ projects connected. At least one is "drifted," at least one is "synced."
**Routes touched**: `/dashboard`, `/settings`

### Steps

1. **Open Dashboard** [CURRENT]: Click "Dashboard" in the sidebar (on mobile: hamburger menu first).
   - **See**: The dashboard page loads with the project table populated.
   - **Verify**: No loading spinner stuck indefinitely. The table renders within 3 seconds.

2. **Read rollup summary** [THIS SPRINT]: Look above the project table for summary cards.
   - **See**: Cards showing: total project count, synced count, drifted count, error count (if any).
   - **Verify**: The drifted card is visually distinct (warning color). The counts are internally consistent (total = synced + drifted + error).

3. **Filter by status** [CURRENT]: Use the status filter dropdown above the table (if present) to show only "Drifted" projects.
   - **See**: The table filters to show only drifted projects. The pagination updates to reflect the filtered count.
   - **Verify**: Clearing the filter restores the full list.

4. **Click drifted project row** [CURRENT]: Click anywhere on a row showing "drifted" status.
   - **See**: The DrawerPeek slides in from the right.
   - **Verify**: The drawer header shows the correct project name. Drift details are visible: commits behind count, list of files that would change. The "Pull" button is prominent.

5. **Execute pull from drawer** [THIS SPRINT]: Click the "Pull" button in the drawer.
   - **See**: Button enters loading state (spinner, disabled). On success, the status in the drawer updates to "synced."
   - **Verify**: The corresponding table row behind the drawer also updates its status. A success toast appears. The rollup cards update their counts.

6. **Navigate to Settings** [THIS SPRINT]: On mobile, tap hamburger first. Click "Settings" in the sidebar.
   - **See**: URL changes to `/settings`. The sidebar highlights the Settings link as active. The Dashboard link is no longer active.
   - **Verify**: The policy classifications table is visible with file patterns and their current classifications.

7. **Return to Dashboard** [CURRENT]: Click "Dashboard" in the sidebar.
   - **See**: Dashboard loads. The project that was just pulled now shows "synced."
   - **Verify**: The table data is fresh (reflects the pull action), not stale cached data.

### Error Variations

- **Pull fails mid-operation**: If the pull API returns an error, verify: the button exits loading state, an error notification appears, the project status does NOT change to "synced," the drawer remains open.
- **Mixed project health**: With projects in synced, drifted, and error states simultaneously, verify: each state renders with a distinct visual indicator, the error project doesn't prevent other projects from loading.
- **Stale data after tab switch**: Switch to another browser tab, wait 30+ seconds, switch back. Verify: dashboard shows current data (auto-refresh or shows staleness indicator).
