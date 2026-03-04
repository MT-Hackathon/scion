# Journey: Settings Management
**Persona**: Sam — The Daily Practitioner
**Viewport**: All (375px, 768px, 1200px)
**Preconditions**: User is on the Dashboard. At least one project is connected.
**Routes touched**: `/dashboard`, `/settings`, `/settings/connect`

### Steps

1. **Navigate to Settings** [THIS SPRINT]: On mobile, tap hamburger first. Click "Settings" in the sidebar.
   - **See**: The settings page loads at `/settings`. A policy classifications table is visible showing file patterns and their classifications (overwrite, template, content_filter, protect, ignore).
   - **Verify**: URL is `/settings`. The table has readable columns. On mobile (375px), the table adapts — either horizontal scroll or card layout. On tablet/desktop, all columns are visible.

2. **Inspect policy classifications** [THIS SPRINT]: Read the policy table.
   - **See**: Rows showing patterns like `.cursor/rules/000-*`, `.cursor/skills/*/SKILL.md`, etc. Each has a classification value.
   - **Verify**: The classifications match the five valid types: overwrite, template, content_filter, protect, ignore. No empty or unknown classifications.

3. **Edit a classification** [THIS SPRINT]: Click the edit control on a row (dropdown, edit icon, or inline edit).
   - **See**: The classification becomes editable — a Select dropdown or Dialog appears with the five valid options.
   - **Verify**: The current value is pre-selected. Selecting a different value visually changes the row. A "Save" or "Apply" action is available.

4. **Save policy change** [THIS SPRINT]: Confirm the edit (click Save, Apply, or similar).
   - **See**: A brief loading indicator. On success, a toast notification confirms the save.
   - **Verify**: The table reflects the new classification. Refreshing the page shows the persisted value.

5. **Navigate to Connect sub-page** [THIS SPRINT]: Find and click a "Connect New Project" button or link within the settings view.
   - **See**: URL changes to `/settings/connect`. The connect form renders within the settings layout context.
   - **Verify**: The sidebar still shows Settings as the active section. A breadcrumb or back link to `/settings` is visible.

6. **Navigate back to Settings** [THIS SPRINT]: Click the back link, breadcrumb, or "Settings" in the sidebar.
   - **See**: Returns to `/settings` with the policy table.
   - **Verify**: The policy change from step 4 is still reflected (not reverted).

7. **Return to Dashboard** [CURRENT]: Click "Dashboard" in the sidebar.
   - **See**: Dashboard loads at `/dashboard`.
   - **Verify**: Navigation is clean — no stale settings state leaking into the dashboard.

### Error Variations

- **Save fails**: If the policy update API returns an error, verify: error notification appears, the table reverts to the previous classification (optimistic save rolled back), the user can retry.
- **Invalid policy state**: If a policy validation endpoint flags a conflict (e.g., overlapping patterns), verify: the error explains what conflicts, the save is blocked, the form is still editable.
- **Connect form from settings**: Verify the connect form at `/settings/connect` behaves identically to the connect form reached from the dashboard empty state (same fields, same validation, same success flow).
