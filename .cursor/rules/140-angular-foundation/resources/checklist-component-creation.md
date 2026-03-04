# Checklist: Component Creation

Validation checklist before creating or modifying Angular components.

---

## Pre-Creation Checklist

- [ ] Search for existing component that can be extended
- [ ] Determine if component should be in `core/` or `features/`
- [ ] Identify required Material modules for imports

---

## Component Structure Checklist

- [ ] No `standalone: true` in decorator (default)
- [ ] `changeDetection: ChangeDetectionStrategy.OnPush` set
- [ ] All dependencies in `imports` array
- [ ] File naming: `kebab-case.component.ts`
- [ ] Class naming: `PascalCase`

---

## Dependency Injection Checklist

- [ ] Using `inject()` function, not constructor injection
- [ ] Services marked as `readonly`
- [ ] Services injected at class body level

```typescript
// CORRECT
export class MyComponent {
  readonly userService = inject(UserService);
  readonly router = inject(Router);
}
```

---

## State Management Checklist

- [ ] Using `signal()` for mutable state
- [ ] Using `computed()` for derived state
- [ ] Using `input()` for component inputs
- [ ] Using `output()` for component outputs
- [ ] No `@Input()` or `@Output()` decorators
- [ ] Using `update()` or `set()`, never `mutate()`

---

## Template Checklist

- [ ] Using `@if`, `@for`, `@switch` control flow
- [ ] No `*ngIf`, `*ngFor`, `*ngSwitch`
- [ ] `@for` includes `track` expression
- [ ] `@for` includes `@empty` block where appropriate
- [ ] Using `[class.x]` instead of `ngClass`
- [ ] Using `[style.x]` instead of `ngStyle`

---

## Host Bindings Checklist

- [ ] Using `host: {}` in decorator
- [ ] No `@HostBinding` or `@HostListener`

---

## Accessibility Checklist

- [ ] Interactive elements are keyboard accessible
- [ ] ARIA labels where semantic HTML insufficient
- [ ] Focus management for dynamic content
- [ ] Color contrast meets WCAG AA (4.5:1)

---

## File Organization Checklist

- [ ] Logic in `.ts` file
- [ ] Styles in `.scss` file
- [ ] Template in `.html` file (unless inline for small component)
- [ ] Spec file created: `.spec.ts`

---

## Service Checklist (if creating service)

- [ ] `@Injectable({providedIn: 'root'})` for singletons
- [ ] Private signals for internal state
- [ ] Public computed for read access
- [ ] Clear method names for state updates

---

## Post-Creation Checklist

- [ ] Component compiles without errors
- [ ] Basic unit test passes
- [ ] No linter warnings
- [ ] Imports are organized (Angular, Material, Project)
