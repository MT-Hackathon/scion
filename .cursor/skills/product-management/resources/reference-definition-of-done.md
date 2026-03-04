# Reference: Definition of Done

Defines what "done" means at each level of granularity.

---

## Per Layer

| Layer | Done When |
|-------|-----------|
| **Requirement** | Feature Card exists with actors, user journey, success criteria, and acceptance tests |
| **Backend API** | Endpoint implemented, validated (`@Valid`), authorized, tested, documented in API spec |
| **Frontend UI** | Component implemented, route-guarded, accessible, tested, responsive |
| **Permissions** | Route guard + API authorization + field-level permissions all enforced |
| **Validation** | Client-side shows inline errors; server-side returns 400 with ProblemDetail |
| **Error Handling** | Network failures show toast/snackbar; never blank page; never raw error |
| **Accessibility** | Keyboard, screen reader, contrast all verified; no automated a11y violations |
| **Tests** | Unit + component + integration tests; all acceptance test scenarios automated |
| **Audit** | Status transitions, field changes, and milestone events recorded with actor |
| **E2E Flow** | Feature works in at least one cross-feature flow (Flows A-D in doc 12) |

---

## Per Feature Card

A Feature Card (F-01 through F-14) is **Done** when:

1. All success criteria checkboxes are checked
2. All acceptance test scenarios have passing automated tests
3. The feature has been tested in its end-to-end flow
4. The Implementation Completeness Matrix shows all layers as "Yes"
5. No known critical or high-severity defects remain
6. Accessibility audit passes with no violations
7. PM has verified the user journey matches expected behavior

---

## Per Git Issue

A git issue is **Done** when:

1. The issue's acceptance criteria (in the issue body) are all satisfied
2. The issue links to the Feature Card it implements
3. Code is merged to the development branch
4. Tests pass in CI
5. The Feature Card's success criteria impacted by this issue are verified
6. If the issue changes the user journey, doc 12 is updated in the same PR

---

## Per Release

A release is **Done** when:

1. All issues in the milestone are closed (Done per above)
2. The Implementation Completeness Matrix reflects current state
3. End-to-end flows (A-D) have been manually walked through
4. No regression in previously completed features
5. Accessibility scan shows no new violations
6. Release notes document which features are new, changed, or fixed

---

## Not Done (Red Flags)

These indicate a feature is NOT done, even if the code works:

| Red Flag | Why It's Not Done |
|----------|-------------------|
| "Works for me locally" | Not verified in CI or other environments |
| "Tests pass but I skipped the error cases" | Acceptance criteria not fully covered |
| "The form works but I didn't check permissions" | Unauthorized users may access it |
| "Backend is done, waiting for frontend" | Feature is not usable until both layers work |
| "It works but the error message says 'undefined'" | Error handling incomplete |
| "The feature works but I didn't update doc 12" | Traceability broken |
| "It's accessible except for keyboard navigation" | Section 508 not met |
