# Examples: Keyboard Navigation

Patterns for keyboard-accessible Angular components.

---

## Focus Management in Angular

### Using host bindings for focus

```typescript
@Component({
  selector: 'app-custom-button',
  template: `<ng-content></ng-content>`,
  host: {
    'role': 'button',
    'tabindex': '0',
    '(keydown.enter)': 'onClick()',
    '(keydown.space)': 'onClick()',
    '(click)': 'onClick()',
  },
})
export class CustomButton {
  readonly clicked = output<void>();

  onClick(): void {
    this.clicked.emit();
  }
}
```

---

## Tab Order Management

### Logical tab order

```html
<!-- Good: Natural tab order follows visual order -->
<header>
  <nav>
    <a href="/">Home</a>
    <a href="/about">About</a>
  </nav>
</header>
<main>
  <h1>Page Title</h1>
  <form>
    <label for="name">Name</label>
    <input id="name" type="text">
    
    <label for="email">Email</label>
    <input id="email" type="email">
    
    <button type="submit">Submit</button>
  </form>
</main>
```

### Skip Navigation Link

```html
<body>
  <a href="#main-content" class="skip-link">
    Skip to main content
  </a>
  <header><!-- ... --></header>
  <main id="main-content" tabindex="-1">
    <!-- Main content -->
  </main>
</body>
```

```scss
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: 8px;
  background: #000;
  color: #fff;
  z-index: 100;

  &:focus {
    top: 0;
  }
}
```

---

## Arrow Key Navigation

### Menu Navigation

```typescript
@Component({
  selector: 'app-menu',
  template: `
    <ul role="menu" (keydown)="onKeydown($event)">
      @for (item of items(); track item.id; let i = $index) {
        <li role="menuitem" 
            [tabindex]="i === focusIndex() ? 0 : -1"
            (click)="selectItem(item)">
          {{ item.label }}
        </li>
      }
    </ul>
  `,
})
export class MenuComponent {
  readonly items = input.required<MenuItem[]>();
  readonly focusIndex = signal(0);

  onKeydown(event: KeyboardEvent): void {
    const items = this.items();
    let index = this.focusIndex();

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        index = (index + 1) % items.length;
        break;
      case 'ArrowUp':
        event.preventDefault();
        index = (index - 1 + items.length) % items.length;
        break;
      case 'Home':
        event.preventDefault();
        index = 0;
        break;
      case 'End':
        event.preventDefault();
        index = items.length - 1;
        break;
    }

    this.focusIndex.set(index);
    this.focusItem(index);
  }

  private focusItem(index: number): void {
    const items = this.elementRef.nativeElement.querySelectorAll('[role="menuitem"]');
    items[index]?.focus();
  }
}
```

---

## Modal Focus Trap

```typescript
import {A11yModule, FocusTrap, FocusTrapFactory} from '@angular/cdk/a11y';

@Component({
  selector: 'app-modal',
  imports: [A11yModule],
  template: `
    <div class="modal-backdrop" (click)="close()"></div>
    <div class="modal" 
         role="dialog" 
         aria-modal="true"
         aria-labelledby="modal-title"
         cdkTrapFocus
         [cdkTrapFocusAutoCapture]="true">
      <h2 id="modal-title">{{ title() }}</h2>
      <div class="modal-content">
        <ng-content></ng-content>
      </div>
      <div class="modal-actions">
        <button (click)="close()">Cancel</button>
        <button (click)="confirm()">Confirm</button>
      </div>
    </div>
  `,
  host: {
    '(keydown.escape)': 'close()',
  },
})
export class ModalComponent {
  readonly title = input.required<string>();
  readonly closed = output<void>();
  readonly confirmed = output<void>();

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    this.confirmed.emit();
  }
}
```

---

## Focus Indicators

```scss
// Global focus styles
:focus {
  outline: 2px solid var(--focus-color, #005fcc);
  outline-offset: 2px;
}

// Remove default and add custom for specific elements
button:focus,
a:focus,
input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 95, 204, 0.5);
}

// Visible only for keyboard focus (optional enhancement)
:focus:not(:focus-visible) {
  outline: none;
  box-shadow: none;
}

:focus-visible {
  outline: 2px solid var(--focus-color, #005fcc);
  outline-offset: 2px;
}
```

---

## Route Change Focus Management

```typescript
import {DestroyRef, inject} from '@angular/core';
import {Router, NavigationEnd} from '@angular/router';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {filter} from 'rxjs/operators';

@Component({...})
export class AppComponent {
  private readonly destroyRef = inject(DestroyRef);
  readonly router = inject(Router);

  constructor() {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        // Focus main content after navigation
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
          mainContent.focus();
        }
      },
      error: (err) => console.error('Navigation error', err),
    });
  }
}
```

---

## Testing Keyboard Navigation

```typescript
describe('keyboard navigation', () => {
  it('should navigate items with arrow keys', () => {
    const menu = fixture.nativeElement.querySelector('[role="menu"]');
    const items = menu.querySelectorAll('[role="menuitem"]');

    // Focus first item
    items[0].focus();
    expect(document.activeElement).toBe(items[0]);

    // Press ArrowDown
    menu.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown'}));
    fixture.detectChanges();
    expect(document.activeElement).toBe(items[1]);

    // Press ArrowUp
    menu.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowUp'}));
    fixture.detectChanges();
    expect(document.activeElement).toBe(items[0]);
  });

  it('should close modal on Escape', () => {
    const closeSpy = vi.spyOn(component.closed, 'emit');
    
    fixture.nativeElement.dispatchEvent(
      new KeyboardEvent('keydown', {key: 'Escape'})
    );
    
    expect(closeSpy).toHaveBeenCalled();
  });
});
```
