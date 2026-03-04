# Specification Completeness Guide

This checklist is an anti-ambiguity filter for feature planning. Use it to ensure behavioral patterns are fully defined before delegating implementation to an Executor.

## How to Use
If a feature touches a pattern below, answer its questions during the planning phase. Any unanswered questions should be explicitly tracked as TODOs or risks in the delegation brief.

## 1. List Pages
- Which columns must be displayed, and which are optional/hidden by default?
- Which columns are sortable, and what is the default sort order (field and direction)?
- What is the default pagination page size, and is it user-configurable?
- What exactly is shown in the empty state when no data exists?
- What is the loading state behavior (skeleton screens, spinners, or progress bars)?
- What are the row-level actions (inline buttons vs. context menu vs. click-to-detail)?
- Are bulk actions required (select multiple)? If so, which actions apply to the selection?
- Which columns should be hidden or collapsed first on smaller screens?

## 2. Search & Filter
- Which specific fields are searchable, and which are filterable?
- What are the matching semantics for search (exact, contains, fuzzy, or starts-with)?
- Do multiple filters combine using AND (restrictive) or OR (additive) logic?
- Is filtering real-time (on change/debounce) or triggered by a "Submit/Apply" button?
- If real-time, what is the debounce timing (e.g., 300ms)?
- Is there a "Clear All" action, and does it reset the URL state?
- Are filter states persisted in the URL for deep-linking and browser history?
- Does the "No Results Found" state differ from the "No Data Exists" empty state?
- Is filtering performed on the server (API) or the client (local data)?

## 3. Forms
- When does validation trigger (on blur, on change, on submit, or progressively)?
- Where are error messages displayed (inline per field, summary at top, or both)?
- How are required fields indicated (asterisk, "(required)" label, or both)?
- Is "Save as Draft" required, or must the form be completed in one session?
- What happens on "Cancel" if the form is dirty (confirmation dialog or immediate discard)?
- What is the success feedback mechanism (toast message, redirect, or inline success)?
- Does the form reset or remain populated after a successful submission?
- In edit mode, how is the initial data fetched and populated (loading state per field)?

## 4. CRUD Operations
- Which fields are user-provided versus system-generated (IDs, timestamps, owners)?
- In the detail view, which related entities or child records must be visible?
- What is the update strategy (optimistic UI updates or pessimistic "wait for server")?
- Is deletion "soft" (archived) or "hard" (purged from DB)?
- What is the specific text for the delete confirmation dialog and its destructive action?
- What are the cascade effects of a deletion on related records?
- Which roles have permission for each specific operation (C, R, U, D)?
- Which field changes must be captured in the audit trail/history?

## 5. Modals & Dialogs
- Does clicking the backdrop or pressing "Escape" dismiss the modal?
- Is support for nested (stacked) modals required for this workflow?
- How does the modal handle content that exceeds the vertical viewport (scrolling)?
- Is form state preserved if a user accidentally dismisses the modal?
- Does the focus trap correctly, and which element receives focus on close?
- What specific action triggers a confirmation dialog (e.g., "Discard Changes")?
- Is the modal size fixed (sm, md, lg) or responsive to its content?

## 6. Wizards & Multi-Step Flows
- Is validation performed per step or only on the final "Submit"?
- Can users navigate backward, skip steps, or jump to arbitrary steps?
- What progress indicator is used (step count, progress bar, or breadcrumbs)?
- Can progress be saved to the server and resumed later?
- How is the browser "Back" button handled within the wizard state?
- Are there data dependencies where a later step changes based on an earlier choice?
- Is the total step count visible to the user at all times?

## 7. Dashboards & Summary Views
- What is the data refresh strategy (manual, polling interval, or real-time websocket)?
- What are the available date range presets (e.g., "Last 7 Days"), and is there a custom picker?
- If one widget fails to load, does it block the rest of the page?
- Are loading states per-widget (independent) or for the entire dashboard?
- How do widgets rearrange or hide on mobile/tablet viewports?
- Is there a "Last Updated" timestamp or data freshness indicator visible?
- Can users drill down from a summary widget to a filtered list page?

## 8. API Endpoints
- What are the request and response shapes (fields, types, required vs. optional)?
- What error codes are returned, and what does the response body contain for each?
- What are the rate limits or throttling rules?
- Is the response paginated? If so, what is the pagination contract (cursor, offset, page)?
- What authentication and authorization does the endpoint require?
- Are there idempotency requirements (safe to retry)?
- What is the expected latency, and is there a timeout contract?
- What side effects does the endpoint trigger (notifications, audit entries, downstream calls)?

## 9. Workflows & State Machines
- What are the valid states, and what are the entry/exit criteria for each?
- What are the allowed transitions, and which role or event triggers each?
- What side effects fire on each transition (notifications, audit log, status propagation)?
- Are there approval gates? Who approves, and what happens on rejection?
- Can a transition be reversed or undone? Under what conditions?
- What happens to in-flight workflows when business rules change?
- Is there a terminal state, and what cleanup occurs when it is reached?

## 10. Permissions & Authorization
- Which roles can perform each operation, and is access scoped (global, agency, team)?
- Are there row-level access rules (users only see their own data, agency-scoped, etc.)?
- What does a permission denial look like to the user (hidden element, disabled control, error message)?
- Are there delegation or impersonation rules (acting on behalf of another user)?
- How are permission changes audited?
- What is the default access for a new role or user (deny-all or inherit)?
