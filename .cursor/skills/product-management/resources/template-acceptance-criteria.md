# Template: Acceptance Criteria

Use this template when writing acceptance criteria for features, sub-features, or git issues.

---

## Format

```
GIVEN [precondition]
WHEN [action]
THEN [expected outcome]
AND [additional outcomes]
```

## Rules

1. **One scenario per block** — Don't combine multiple test cases
2. **Use real names** — Actual role names, status codes, field names, and route paths
3. **Cover all paths** — Happy, error, permission denied, edge case
4. **Be testable** — Every criterion must be translatable to an automated test
5. **Be specific** — "User sees an error" is bad; "Validation error appears on the itemName field with message 'Item name is required'" is good

---

## Required Scenarios Per Feature Type

### Form Feature (e.g., refinement, entity CRUD)

```
# Happy Path
GIVEN a [role] with [permission] on the [form route]
WHEN they fill all required fields and click Save
THEN the data persists to the database
AND a success notification appears
AND the form resets or navigates to the list view

# Validation Error
GIVEN a [role] on the [form route]
WHEN they submit with [specific field] empty
THEN a validation error appears on [specific field]: "[error message]"
AND the form is NOT submitted

# Permission Denied
GIVEN a [role WITHOUT permission] navigating to [form route]
WHEN the route guard evaluates
THEN they are redirected to [default route]
AND a notification explains the denial

# Server Error
GIVEN a [role] submitting a valid form
WHEN the server returns a 500 error
THEN an error notification appears: "Unable to save. Please try again."
AND the form data is preserved (not cleared)
```

### Workflow Action (e.g., approve, deny, submit)

```
# Happy Path
GIVEN a [role] viewing a request in [status]
WHEN they click [action button]
THEN the request status transitions to [new status]
AND [side effects: notifications, audit entries, queue updates]

# Confirmation Required
GIVEN a [role] clicking [destructive action]
WHEN the confirmation dialog appears
THEN the dialog shows [specific warning message]
AND clicking Cancel returns to the previous state without changes

# Separation of Duty
GIVEN a user who created the request
WHEN they attempt to [approve/deny] it
THEN the action is blocked
AND a message explains: "You cannot approve your own request"

# Concurrent Modification
GIVEN two approvers viewing the same request
WHEN Approver A approves while Approver B is still reviewing
THEN Approver B's page reflects the updated state
AND Approver B cannot duplicate the approval
```

### List/Dashboard Feature (e.g., queue, entity list)

```
# Data Display
GIVEN a [role] with [N] items in their [queue/list]
WHEN they navigate to [route]
THEN all [N] items are displayed with [specific columns]
AND items are sorted by [default sort field] descending

# Filtering
GIVEN a [role] viewing [list] with items across multiple [filter dimension]
WHEN they filter by [specific value]
THEN only matching items are shown
AND the count updates to reflect filtered results

# Empty State
GIVEN a [role] with no items in their [queue/list]
WHEN they navigate to [route]
THEN a message displays: "[No items message]"
AND [optional: CTA button for creating new item]

# Pagination (if applicable)
GIVEN a [role] with more than [page size] items
WHEN they navigate to page 2
THEN the next set of items loads
AND the pagination indicator shows current position
```

---

## Example: F-01 Procurement Request Intake

```
# Happy Path — Create and Submit Draft
GIVEN a logged-in State Employee (REQUESTER role)
WHEN they navigate to /requests/new
AND fill: itemName="Office Chairs", description="50 ergonomic chairs", estimatedCost=15000, purchaseCategory=COMMODITY
AND click Submit
THEN the request status transitions from DRAFT to INTAKE_SUBMITTED
AND the request appears in the APO queue for the employee's purchasing agency
AND a success notification appears: "Request submitted successfully"

# Validation — Missing Required Fields
GIVEN a REQUESTER on /requests/new
WHEN they click Submit without entering an itemName
THEN a validation error appears on the itemName field: "Item name is required"
AND the form is NOT submitted
AND the field is highlighted in red

# Attachment — Successful Upload
GIVEN a REQUESTER creating a new request
WHEN they drag a PDF file (< 10MB) onto the upload zone
THEN a progress indicator shows upload percentage
AND after completion, the file appears in the attachment list with status "Scanning..."
AND after virus scan, the status updates to "Clean" with a checkmark icon

# Attachment — Rejected File Type
GIVEN a REQUESTER creating a new request
WHEN they attempt to upload a .exe file
THEN the upload is rejected immediately
AND an error message appears: "File type not allowed. Supported formats: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG"
```
