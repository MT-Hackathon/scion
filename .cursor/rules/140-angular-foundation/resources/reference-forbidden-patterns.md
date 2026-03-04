# Reference: Forbidden Angular Patterns

Patterns that MUST NOT be used in this Angular 21 codebase.

---

## Forbidden Decorators

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `@Input()` | `input()` | Signal-based inputs are reactive |
| `@Output()` | `output()` | Signal-based outputs are cleaner |
| `@HostBinding()` | `host: {}` in decorator | Consolidates host bindings |
| `@HostListener()` | `host: {}` in decorator | Consolidates host listeners |

---

## Forbidden Directives

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `*ngIf` | `@if` | Built-in control flow is faster |
| `*ngFor` | `@for` with `track` | Built-in control flow, mandatory tracking |
| `*ngSwitch` | `@switch` | Built-in control flow |
| `ngClass` | `[class.name]="expr"` | Direct binding is simpler |
| `ngStyle` | `[style.prop]="expr"` | Direct binding is simpler |

---

## Forbidden Component Patterns

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `standalone: true` in decorator | (omit entirely) | Default in Angular 21 (Enforced by ESLint: `prefer-standalone`) |
| Default change detection | `OnPush` strategy | Mandatory for performance (Enforced by ESLint: `prefer-on-push-component-change-detection`) |
| Constructor injection | `inject()` function | Cleaner, works in functions |
| NgModules for features | Standalone imports | Simpler dependency graph |
| `trackBy` function | `track` expression in `@for` | Built into new syntax |

---

## Forbidden Signal Patterns

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `signal.mutate()` | `signal.update()` | `mutate` is deprecated |
| Direct signal assignment | `signal.set()` | Signals are not assignable |

---

## Forbidden Form Patterns

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| Template-driven forms | Reactive forms | Better type safety, testability |
| `[(ngModel)]` in complex forms | `FormControl` | Explicit control |

---

## Forbidden Image Patterns

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `<img src="...">` for static | `NgOptimizedImage` | LCP optimization |
| Missing width/height | Explicit dimensions | Prevents layout shift |

---

## Example Migrations

### Input Migration

```typescript
// FORBIDDEN
@Component({...})
export class OldComponent {
  @Input() userId: string;
  @Input() showDetails = false;
}

// CORRECT
@Component({...})
export class NewComponent {
  readonly userId = input.required<string>();
  readonly showDetails = input(false);
}
```

### Control Flow Migration

```html
<!-- FORBIDDEN -->
<div *ngIf="isVisible; else hiddenTemplate">Visible</div>
<ng-template #hiddenTemplate>Hidden</ng-template>

<!-- CORRECT — @else here is template rendering control flow (visual state), not logic branching.
     The "zero else in logic functions" rule applies to TypeScript/Python, not HTML templates. -->
@if (isVisible()) {
  <div>Visible</div>
} @else {
  <div>Hidden</div>
}
```

### Host Binding Migration

```typescript
// FORBIDDEN
@Component({...})
export class OldComponent {
  @HostBinding('class.active') isActive = false;
  @HostListener('click') onClick() { ... }
}

// CORRECT
@Component({
  host: {
    '[class.active]': 'isActive()',
    '(click)': 'onClick()',
  },
})
export class NewComponent {
  readonly isActive = signal(false);
  onClick(): void { ... }
}
```

### Class Binding Migration

```html
<!-- FORBIDDEN -->
<div [ngClass]="{'active': isActive, 'disabled': isDisabled}">

<!-- CORRECT -->
<div [class.active]="isActive()" [class.disabled]="isDisabled()">
```
