# Checklist: Feature Completeness

Use this checklist to verify a feature is complete before marking it Done. Each feature type has a base checklist plus type-specific items.

---

## Base Checklist (All Features)

### Requirements Traceability
- [ ] Feature traces to a Feature Card in `docs/requirements/12-feature-interaction-map.md`
- [ ] If from a git issue, the issue references the Feature Card ID (e.g., F-01)
- [ ] All success criteria from the Feature Card are addressed
- [ ] Acceptance test scenarios are documented (Given/When/Then)

### Backend Implementation
- [ ] API endpoint(s) exist and return correct responses
- [ ] DTO validation (`@Valid`, `@NotNull`, `@Size`, etc.) enforced
- [ ] Server-side authorization checked (role + permission)
- [ ] Error responses follow RFC 7807 ProblemDetail format
- [ ] Audit trail records state transitions and field changes

### Frontend Implementation
- [ ] Route exists and is accessible from navigation menu (if applicable)
- [ ] Route guard enforces permission check
- [ ] Component renders correctly with real data
- [ ] Loading state shown while data fetches
- [ ] Error state shown on API failure (not blank page)
- [ ] Form validation shows inline errors with specific messages

### Accessibility (Section 508 / WCAG 2.1 AA)
- [ ] Keyboard navigable (Tab, Enter, Escape for dialogs)
- [ ] Screen reader announces form labels, errors, and status changes
- [ ] Color contrast ratio >= 4.5:1 for text, >= 3:1 for large text
- [ ] Focus management: focus moves logically, trapped in dialogs
- [ ] ARIA labels on interactive elements without visible text

### Tests
- [ ] Unit tests for services and business logic
- [ ] Component tests for UI rendering and interaction
- [ ] Integration tests for API endpoints
- [ ] Each acceptance test scenario has a corresponding automated test
- [ ] Tests pass in CI (`npm run test:ci` for frontend, `./gradlew test` for backend)

### Cross-Feature Verification
- [ ] Feature works in at least one end-to-end flow (Flows A-D in doc 12)
- [ ] No regression in dependent features
- [ ] Implementation Completeness Matrix updated in doc 12

---

## Type-Specific Checklists

### Form Feature (intake, refinement, entity CRUD, delegation)

- [ ] All required fields have validation with specific error messages
- [ ] Optional fields are clearly distinguished from required fields
- [ ] Form preserves data on validation failure (no data loss)
- [ ] Form preserves data on server error (no data loss)
- [ ] Success action shows notification and navigates appropriately
- [ ] Role-based field permissions applied (read-only vs editable)
- [ ] Long forms have section navigation or progress indicators
- [ ] Mobile responsive: form usable on tablet width (768px+)

### Workflow Action (approve, deny, submit, elevate, cancel)

- [ ] Action button visible only to authorized roles
- [ ] Confirmation dialog for destructive/irreversible actions
- [ ] Status transition fires correctly (from → to)
- [ ] Side effects execute (notifications sent, audit recorded, queues updated)
- [ ] Separation of duty enforced (cannot approve own request)
- [ ] Concurrent modification handled (optimistic locking or refresh)
- [ ] Error rollback: failed action does not leave partial state

### List/Dashboard Feature (queue, entity list, approver dashboard)

- [ ] List shows correct data scoped to user's role/agency
- [ ] Default sort order is meaningful (most recent, highest priority)
- [ ] Filtering works for each filterable dimension
- [ ] Empty state message is helpful (not just blank)
- [ ] Pagination works for large datasets (or virtual scroll)
- [ ] Click-through navigation to detail view works
- [ ] Metrics/counters are accurate and update on action

### Visualization Feature (approval path, workflow progress)

- [ ] Visualization reflects current real-time state
- [ ] Each element is interactive or clearly informational
- [ ] Status changes are visually distinct (color + icon, not color alone)
- [ ] Accessible: screen reader can describe the visualization state
- [ ] Mobile responsive: visualization adapts to narrow viewports

---

## How to Use This Checklist

1. **Before implementation**: Copy the Base + Type-Specific checklist into the git issue or task
2. **During implementation**: Check items as they are verified
3. **Before marking Done**: All items must be checked or explicitly marked N/A with justification
4. **During review**: Reviewer uses the checklist to validate completeness
