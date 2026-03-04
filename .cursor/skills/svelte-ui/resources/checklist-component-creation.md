# Checklist: Component Creation

Pre-flight checklist for creating Svelte components and updating tokens.

---

## Before Creating a Component

- [ ] Search for existing similar components
- [ ] Verify component name follows naming conventions
- [ ] Determine if component needs to be in `$lib/components/custom/` or route-specific

## Component Structure

- [ ] Use `<script lang="ts">`
- [ ] Define props using `let { prop } = $props()`
- [ ] Define state using `let state = $state(value)`
- [ ] Define derived values using `let derived = $derived(value)`
- [ ] Define effects using `$effect(() => { ... })`
- [ ] Use Svelte 5 syntax exclusively (no Svelte 4 patterns)

## Styling

- [ ] Use Tailwind classes with design tokens
- [ ] Use `var(--token-name)` for direct token access if needed
- [ ] Never hardcode colors or spacing values
- [ ] Never create per-component color variables
- [ ] Only use `<style>` for truly unique cases (not colors)

## Forms & State

- [ ] Form values bind to shared store/resource (never local state)
- [ ] Use shadcn Input for text inputs (never plain `<input>`)
- [ ] Use form store from `configFormStores.ts` for config forms
- [ ] Validate before saving
- [ ] Show error messages from form store errors

## shadcn-svelte

- [ ] Import from `$lib/components/ui/[component]`
- [ ] Use Button for actions
- [ ] Use Input for text fields
- [ ] Use Select for dropdowns (accessibility)
- [ ] Use Dialog for modals
- [ ] Use Toast for notifications

## Accessibility

- [ ] Add ARIA labels where appropriate
- [ ] Ensure keyboard navigation works
- [ ] Add focus styles using design tokens
- [ ] Test with keyboard only
- [ ] Verify screen reader compatibility

## Canvas/Node Components

- [ ] Use design tokens from `cssVariableSync.ts`
- [ ] Reference `SourceNode.svelte` for visual patterns
- [ ] Follow gradient, shadow, overlay sequence
- [ ] Implement selected state styling
- [ ] Test with both light and dark themes

## Before Committing

- [ ] Component renders without errors
- [ ] Console is clean (no warnings)
- [ ] TypeScript types are correct
- [ ] Component works in both light and dark themes
- [ ] Responsive behavior is correct
- [ ] Loading states are handled
- [ ] Error states are handled

---

## Token Update Workflow

### Before Adding New Tokens

- [ ] Search for existing similar tokens
- [ ] Verify token name follows naming convention
- [ ] Determine if token is theme-specific or global
- [ ] Check if Tailwind utility can cover the use case

### Adding New Token

1. **Update settings JSON**
   - [ ] Add token to appropriate section
   - [ ] Add value for light theme
   - [ ] Add value for dark theme (if theme-specific)

2. **Update TypeScript Types**
   - [ ] Add property to corresponding interface
   - [ ] Ensure type matches JSON structure

3. **Update CSS Variable Sync**
   - [ ] Add sync logic for new token
   - [ ] Verify token is emitted to `:root` style

4. **Test**
   - [ ] Start dev server
   - [ ] Verify token appears in browser dev tools
   - [ ] Test in light theme
   - [ ] Test in dark theme
   - [ ] Test theme toggle

### Common Token Issues

**Token not updating:**
- [ ] Restart dev server (settings changes require restart)
- [ ] Clear browser cache
- [ ] Verify cssVariableSync is running

**Token value wrong:**
- [ ] Verify correct theme is active
- [ ] Check settings JSON has correct value
- [ ] Inspect `:root` in browser dev tools
