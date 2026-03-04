# Reference: ARIA Patterns

Common ARIA patterns for accessible Angular components.

---

## Labels

| Attribute | Use Case | Example |
|-----------|----------|---------|
| `aria-label` | Label not visible in UI | `<button aria-label="Close dialog">X</button>` |
| `aria-labelledby` | Label from another element | `<div aria-labelledby="section-title">` |
| `aria-describedby` | Additional description | `<input aria-describedby="password-hint">` |

---

## State

| Attribute | Use Case | Example |
|-----------|----------|---------|
| `aria-expanded` | Expandable content | `<button aria-expanded="false">` |
| `aria-selected` | Selectable items | `<li aria-selected="true">` |
| `aria-checked` | Checkable items | `<div role="checkbox" aria-checked="false">` |
| `aria-pressed` | Toggle buttons | `<button aria-pressed="true">` |
| `aria-current` | Current item | `<a aria-current="page">` |
| `aria-disabled` | Disabled state | `<button aria-disabled="true">` |

---

## Live Regions

| Attribute | Use Case | Example |
|-----------|----------|---------|
| `aria-live="polite"` | Non-urgent updates | Status messages, search results |
| `aria-live="assertive"` | Urgent updates | Error messages, alerts |
| `aria-atomic="true"` | Announce entire region | When partial updates confuse |
| `aria-busy="true"` | Loading content | Spinner containers |

```html
<!-- Status announcement -->
<div aria-live="polite" aria-atomic="true">
  {{ statusMessage() }}
</div>

<!-- Error announcement -->
<div role="alert" aria-live="assertive">
  {{ errorMessage() }}
</div>
```

---

## Roles

### Landmark Roles

| Role | Element Equivalent | Use |
|------|-------------------|-----|
| `banner` | `<header>` | Page header |
| `navigation` | `<nav>` | Navigation |
| `main` | `<main>` | Main content |
| `contentinfo` | `<footer>` | Page footer |
| `complementary` | `<aside>` | Sidebar |
| `region` | `<section>` | Named section |

### Widget Roles

| Role | Use Case |
|------|----------|
| `button` | Clickable element that isn't `<button>` |
| `dialog` | Modal dialog |
| `alertdialog` | Alert requiring response |
| `tab` / `tablist` / `tabpanel` | Tab interface |
| `menu` / `menuitem` | Dropdown menu |
| `listbox` / `option` | Selection list |

---

## Common Patterns

### Modal Dialog

```html
<div role="dialog" 
     aria-modal="true" 
     aria-labelledby="dialog-title"
     aria-describedby="dialog-description">
  <h2 id="dialog-title">Confirm Action</h2>
  <p id="dialog-description">Are you sure you want to proceed?</p>
  <button>Cancel</button>
  <button>Confirm</button>
</div>
```

### Tabs

```html
<div role="tablist" aria-label="Account settings">
  <button role="tab" aria-selected="true" aria-controls="panel-1" id="tab-1">
    Profile
  </button>
  <button role="tab" aria-selected="false" aria-controls="panel-2" id="tab-2">
    Security
  </button>
</div>
<div role="tabpanel" id="panel-1" aria-labelledby="tab-1">
  Profile content
</div>
<div role="tabpanel" id="panel-2" aria-labelledby="tab-2" hidden>
  Security content
</div>
```

### Accordion

```html
<div>
  <h3>
    <button aria-expanded="true" aria-controls="section-1">
      Section 1
    </button>
  </h3>
  <div id="section-1">Section 1 content</div>
  
  <h3>
    <button aria-expanded="false" aria-controls="section-2">
      Section 2
    </button>
  </h3>
  <div id="section-2" hidden>Section 2 content</div>
</div>
```

### Loading State

```html
<div aria-busy="true" aria-live="polite">
  <span class="sr-only">Loading...</span>
  <mat-spinner></mat-spinner>
</div>
```

---

## Angular CDK Integration

### LiveAnnouncer

```typescript
import {LiveAnnouncer} from '@angular/cdk/a11y';

export class MyComponent {
  readonly announcer = inject(LiveAnnouncer);

  onSave(): void {
    // ... save logic
    this.announcer.announce('Changes saved successfully', 'polite');
  }

  onError(): void {
    this.announcer.announce('Error: Please try again', 'assertive');
  }
}
```

### FocusTrap

```typescript
import {A11yModule} from '@angular/cdk/a11y';

@Component({
  imports: [A11yModule],
  template: `
    <div cdkTrapFocus [cdkTrapFocusAutoCapture]="true">
      <h2>Modal Content</h2>
      <button>Action</button>
      <button (click)="close()">Close</button>
    </div>
  `,
})
export class ModalComponent { }
```

### FocusMonitor

```typescript
import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {FocusMonitor} from '@angular/cdk/a11y';

export class MyComponent {
  private readonly destroyRef = inject(DestroyRef);
  readonly focusMonitor = inject(FocusMonitor);

  constructor() {
    this.focusMonitor.monitor(this.elementRef)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (origin) => {
          // origin: 'mouse' | 'keyboard' | 'touch' | 'program' | null
        },
        error: (err) => console.error('Focus monitor error', err),
      });

    this.destroyRef.onDestroy(() => {
      this.focusMonitor.stopMonitoring(this.elementRef);
    });
  }
}
```
