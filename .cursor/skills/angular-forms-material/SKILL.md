---
name: angular-forms-material
description: "Governs Angular reactive forms, Material component patterns, and Material Design 3 token governance: FormGroup, FormBuilder, FormArray, validators, MatTable, MatDialog, design tokens, color palettes, typography, and CSS variables. Use when building forms, data tables, dialogs, Material UI components, or configuring token-based visual consistency. DO NOT use for HTTP requests (see angular-http-reactive) or accessibility requirements (see accessibility)."
---

<ANCHORSKILL-ANGULAR-FORMS-MATERIAL>

# Angular Forms & Material

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Examples: Reactive Forms](resources/examples-reactive-forms.md)
- [Examples: Material Forms](resources/examples-material-forms.md)
- [Examples: Material Tables](resources/examples-material-tables.md)
- [Reference: Validation Patterns](resources/reference-validation-patterns.md)
- [Reference: M3 Palettes](resources/reference-m3-palettes.md)
- [Example: Theme Service](resources/examples-theme-service.md)
- [Blueprint: Validators](blueprints/validators.ts)
- [Blueprint: Theme Service](blueprints/theme.service.ts)
- [Cross References](resources/cross-references.md)

## Core Concepts

### Typed Reactive Forms
Always use typed `FormGroup`, `FormControl`, and `FormArray` for type safety.

```typescript
interface UserForm {
  firstName: FormControl<string>;
  lastName: FormControl<string>;
  email: FormControl<string>;
  roles: FormArray<FormControl<string>>;
}

const form = new FormGroup<UserForm>({
  firstName: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  lastName: new FormControl('', { nonNullable: true }),
  email: new FormControl('', { nonNullable: true, validators: [Validators.email] }),
  roles: new FormArray<FormControl<string>>([])
});
```

### FormBuilder
Use `FormBuilder` (or `nonNullable` form builder) for cleaner syntax.

```typescript
private fb = inject(FormBuilder);
private nfb = inject(NonNullableFormBuilder);

form = this.nfb.group({
  name: ['', [Validators.required]],
  address: this.nfb.group({
    street: [''],
    city: ['']
  })
});
```

### Material Form Field Integration
Ensure `MatFormField` wraps `matInput`, `matSelect`, etc., and includes `mat-error`.

```html
<mat-form-field appearance="outline">
  <mat-label>Email</mat-label>
  <input matInput [formControl]="emailControl" placeholder="Ex. pat@example.com">
  @if (emailControl.hasError('email')) {
    <mat-error>Please enter a valid email address</mat-error>
  }
  @if (emailControl.hasError('required')) {
    <mat-error>Email is <strong>required</strong></mat-error>
  }
</mat-form-field>
```

### Signal Effects for Form Control State
Prefer `effect()` over template `[disabled]` bindings for reactive permission-driven enable/disable. Use `{emitEvent: false}` to prevent form value change events.

```typescript
effect(() => {
  const action = this.permission() === 'WRITE' ? 'enable' : 'disable';
  control[action]({emitEvent: false});
});
```

### Data Tables (MatTable)
Use `MatTable` with `MatSort` and `MatPaginator` for enterprise data display.

- **Sorting**: Bind `[matSortActive]` and `(matSortChange)`.
- **Pagination**: Use `MatPaginator` with `[pageSizeOptions]`.
- **Selection**: Use `SelectionModel` from `@angular/cdk/collections`.

### Dialog/Modal Patterns
Use `MatDialog` for modals.

- Pass data using `MAT_DIALOG_DATA`.
- Return results via `dialogRef.close(result)`.
- Use `MatDialogModule` components: `mat-dialog-title`, `mat-dialog-content`, `mat-dialog-actions`.

### Conditional Form Layouts
Use `computed()` signals to derive visibility from form state and `@if` blocks for rendering.

```typescript
// Component: Derive visibility from form value signal
category = toSignal(this.form.controls.category.valueChanges);
isIT = computed(() => this.category() === 'IT');
```

```html
<!-- Template: Conditional section -->
@if (isIT()) {
  <div class="it-fields-section">
    <mat-form-field>...</mat-form-field>
  </div>
}
```

### Display Name Options for Select Fields

For `mat-select` dropdowns with domain values, use `DisplayNameRegistry.options(domain)` to get the option list. The registry returns `LabeledValue[]` with `{ code, displayName }` shape.

```html
@for (option of registry.options('contractType'); track option.code) {
  <mat-option [value]="option.code">{{ option.displayName }}</mat-option>
}
```

For inline display of a single value, use the pipe: `{{ status | displayName:'requestStatus' }}`.

**Anti-pattern**: Never define `const OPTIONS = [{value: '...', label: '...'}]` arrays in components — these belong in the backend `DisplayNameRegistry`.

### Component/Service Decomposition (Facade Pattern)

Mandatory when a Component exceeds **500 lines** or a Service exceeds **400 lines**.
- **The Facade**: A dedicated class/service (e.g., `{Name}Facade`) that manages component state, business logic, and interaction with domain services.
- **Logic Extraction**: Move request builders, progress calculation, complex validation helpers, and error mapping to the facade.
- **Clean Component**: The component remains focused on lifecycle events, template bindings, and user action handlers.

## Design Token System (M3)

### Core Theme Configuration
- **Typography**: Use self-hosted Inter as the default UI typeface.
- **Density**: Default to compact `-1` for enterprise workflows.
- **Neutrals**: Use zinc-based neutral palettes (avoid blue-tinted neutrals).
- **Active state**: Navigation active state must use `color-mix(in srgb, var(--mat-sys-primary) 8%, transparent)`, not `primary-container`.

### Token Architecture
- **Material tokens**: Use `--mat-sys-*` for Material color and typography system values.
- **App tokens**: Use `--app-*` for spacing, radius, and motion semantics.
- **Shapes**: Set shape globally from root tokens (standard radius `--app-radius-md`).
- **Backgrounds**: App shell surfaces should map to `--mat-sys-surface-container-lowest`.

### Semantic Color Extensions
- Define explicit semantic tokens for Success, Warning, and Info states.
- Use `light-dark(light_value, dark_value)` patterns so semantic tokens adapt across schemes.

### Anti-Patterns
- Do not hardcode layout sizing with `px` when token values exist.
- Do not re-introduce Sass shorthand aliases for design primitives; use CSS variables.
- Do not set shape tokens per component; maintain a single root token source.
- In global `style.scss`, use explicit relative imports (`./` or `../`) for repo-local Sass modules to avoid Sass resolution ambiguity.

</ANCHORSKILL-ANGULAR-FORMS-MATERIAL>
