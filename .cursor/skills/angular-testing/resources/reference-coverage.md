# Coverage Reference: Angular + v8

## Template Function Instrumentation

Angular's template compiler generates JavaScript functions from template control flow (`@if`, `@for`) and event bindings (`(click)=`). The v8 coverage provider instruments these generated functions. However:

- **Inline templates** (`template: \`...\``): The generated functions are compiled into the component's `.js` module. Coverage counts appear against the `.ts` file, but v8 cannot source-map them back to HTML lines — the report shows inflated TS function counts while template-bound functions appear uncovered.
- **External templates** (`templateUrl: './x.component.html'`): The compiler generates a separate instrumentation boundary. Coverage for template functions appears as HTML file coverage in the report.

**Mandate**: All components MUST use `templateUrl` for accurate function coverage reporting. This is not a style preference — it determines whether template-bound functions appear in coverage reports at all.

**Impact**: `assignments-dashboard` went from 25% → 94% function coverage after extracting its 132-line inline template. No new tests needed — just the extraction.

## overrideComponent and Coverage

`TestBed.overrideComponent(Component, { set: { template: '<div></div>' }})` causes v8 to instrument the stub template, not the real one. The `.html` file shows 0% coverage.

**Guidance**: When coverage completeness is required, avoid template stubs. Import real component dependencies into TestBed instead. `overrideComponent` trades template coverage for test isolation — make that trade deliberately and document why.

## Coverage Threshold Configuration

Thresholds are enforced in `vitest.config.ts`:

```typescript
coverage: {
  thresholds: {
    statements: 90,
    branches: 85,
    functions: 90,
    lines: 90,
  },
}
```

CI (`npm run test:ci`) fails if any metric drops below these thresholds.

## GitLab Coverage Regex

Angular 21's `@angular/build:unit-test` builder suppresses the `text-summary` reporter output. Only the `text` table format appears in stdout. The GitLab CI regex must match the table format:

```yaml
coverage: '/All\sfiles[^|]*\|\s*([\d.]+)/'
```

This parses the statements percentage from the "All files" row of Vitest's coverage table.
