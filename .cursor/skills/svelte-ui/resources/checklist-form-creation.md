# Checklist: Form Creation

Pre-flight checklist for creating or refactoring form components.

---

## Mandatory Search Locations

Before adding or refactoring any form, search these files first:

- [ ] Canonical form components (e.g., `ApiSourceFormEnhanced.svelte`) for field layout patterns
- [ ] `src/frontend/src/app.css` for `.node-select-*` and `.node-text-input` classes
- [ ] `src/frontend/src/lib/utils/validation.ts` for shared validation helpers
- [ ] `src/frontend/src/lib/config/formConfig.ts` for shared option sets

## Validation Steps

1. [ ] **Field Parity** - New form includes every field from source or documents differences
2. [ ] **Styling Tokens** - Apply `.node-select-trigger`, `.node-select-content`, `.node-text-input` to controls
3. [ ] **Accent Propagation** - Parent wrapper sets `--active-node-color` for controls to inherit
4. [ ] **Validation Helpers** - Use shared validation from `$lib/utils/validation.ts`
5. [ ] **Store Alignment** - Form stores accept same props/handlers and emit identical payload shapes

## Form Structure

- [ ] Use form store from `configFormStores.ts` (not local state)
- [ ] Form values bind to shared store (never local variables)
- [ ] Use shadcn Input for text inputs (never plain `<input>`)
- [ ] Use shadcn Select for dropdowns (accessibility)
- [ ] Include loading state handling
- [ ] Include error state display

## Validation

- [ ] Using Zod for schema validation
- [ ] Blur validation is immediate
- [ ] Change validation is debounced (300ms)
- [ ] Submit runs full schema validation
- [ ] Errors display inline below fields
- [ ] Error summary at form top
- [ ] Error messages are actionable

## Test Endpoint (if applicable)

- [ ] "Test Endpoint" button below URL field
- [ ] States: Idle → Loading → Success/Error
- [ ] Timeout: 10s maximum
- [ ] Credentials redacted in preview
- [ ] Error messages are specific

## Anti-patterns (Code Review Reject)

- [ ] NOT hardcoding colors on inputs
- [ ] NOT using local state for form values
- [ ] NOT using plain `<input>` elements
- [ ] NOT creating new select/input classes
- [ ] NOT omitting fields without justification
- [ ] NOT forgetting accent context from parent
