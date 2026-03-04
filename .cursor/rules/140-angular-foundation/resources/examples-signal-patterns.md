# Examples: Signal Patterns

Signal patterns for Angular 21 state management.

---

## Basic Signal Usage

```typescript
import {signal, computed} from '@angular/core';

// Mutable state
readonly count = signal(0);

// Derived state (computed)
readonly doubleCount = computed(() => this.count() * 2);

// Reading values (call the signal)
const currentCount = this.count();

// Setting values
this.count.set(5);

// Updating based on previous value
this.count.update(prev => prev + 1);
```

---

## Input Signals

```typescript
import {Component, input} from '@angular/core';

@Component({
  selector: 'app-user-card',
  template: `<div>{{ userName() }}</div>`,
})
export class UserCard {
  // Required input
  readonly userId = input.required<string>();

  // Optional input with default
  readonly showAvatar = input(true);

  // Optional input without default
  readonly userName = input<string>();
}
```

**Usage in parent:**

```html
<app-user-card [userId]="'123'" [userName]="currentUser().name" />
```

---

## Output Signals

```typescript
import {Component, output} from '@angular/core';

@Component({
  selector: 'app-button',
  template: `<button (click)="handleClick()">Click me</button>`,
})
export class AppButton {
  readonly clicked = output<void>();
  readonly valueChanged = output<string>();

  handleClick(): void {
    this.clicked.emit();
  }

  updateValue(newValue: string): void {
    this.valueChanged.emit(newValue);
  }
}
```

**Usage in parent:**

```html
<app-button (clicked)="onButtonClick()" (valueChanged)="onValueChange($event)" />
```

---

## Computed with Dependencies

```typescript
import {computed, signal} from '@angular/core';

readonly firstName = signal('John');
readonly lastName = signal('Doe');

// Computed automatically tracks dependencies
readonly fullName = computed(() => {
  return `${this.firstName()} ${this.lastName()}`;
});

// Computed with conditional logic
readonly displayName = computed(() => {
  if (this.isAnonymous()) {
    return 'Anonymous User';
  }
  return this.fullName();
});
```

---

## Signal in Service for State Management

```typescript
import {Injectable, signal, computed} from '@angular/core';

interface User {
  id: string;
  name: string;
  role: string;
}

@Injectable({providedIn: 'root'})
export class UserService {
  // Private signals for state
  private readonly currentUser = signal<User | null>(null);
  private readonly isLoading = signal(false);

  // Public computed for read access
  readonly user = computed(() => this.currentUser());
  readonly loading = computed(() => this.isLoading());
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  readonly isAdmin = computed(() => this.currentUser()?.role === 'admin');

  // Methods to update state
  setUser(user: User): void {
    this.currentUser.set(user);
  }

  clearUser(): void {
    this.currentUser.set(null);
  }

  setLoading(loading: boolean): void {
    this.isLoading.set(loading);
  }
}
```

---

## WritableSignal Type Annotations

Show when to use explicit `WritableSignal<T>` type annotations:

```typescript
import {Injectable, signal, WritableSignal} from '@angular/core';

@Injectable({providedIn: 'root'})
export class ProfileService {
  // Explicit type annotation when the type is complex or for clarity
  private readonly isAuthenticated: WritableSignal<boolean> = signal(false);
  
  // Type inference works for simple cases
  private readonly lastCheckTime = signal(Date.now());
}
```

> **Why This Matters**: Use `WritableSignal<T>` when you need to pass the signal as a parameter or when type inference doesn't suffice for complex types.

---

## Signal Encapsulation with asReadonly()

The canonical pattern for service state encapsulation, using `ThemeService` as the reference:

```typescript
import {Injectable, signal} from '@angular/core';

@Injectable({providedIn: 'root'})
export class ThemeService {
  // Private mutable signal with underscore prefix
  private readonly _isDarkMode = signal<boolean>(false);
  
  // Public readonly accessor via asReadonly()
  readonly isDarkMode = this._isDarkMode.asReadonly();
  
  // State mutations through dedicated methods
  toggle(): void {
    const isDark = !this._isDarkMode();
    this.apply(isDark);
  }
  
  // Side effects applied after state update
  private apply(isDark: boolean): void {
    this._isDarkMode.set(isDark);
    // Apply DOM changes, storage, etc.
  }
}
```

**Key points:**
- Private signal with underscore prefix
- Public readonly via `asReadonly()` - consumers cannot mutate
- Mutations through dedicated methods that can apply side effects

> **Why This Matters**: This ensures encapsulation and unidirectional data flow, making state changes predictable and easier to debug.

---

## Safe Browser API Access Patterns

When signals interact with browser APIs that may fail (SSR, private mode):

```typescript
// Safe localStorage access - failure-tolerant for private mode
private readStoredPreference(): boolean | null {
  try {
    const raw = window.localStorage.getItem('app:theme:isDark');
    if (raw === null) return null;
    return raw === 'true';
  } catch {
    return null; // Private mode or SSR
  }
}

private storePreference(isDark: boolean): void {
  try {
    window.localStorage.setItem('app:theme:isDark', String(isDark));
  } catch {
    // Ignore storage failures (e.g., private mode)
  }
}

// Safe matchMedia access - SSR guardrail
private getSystemPrefersDark(): boolean {
  try {
    return !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch {
    return false; // SSR or unsupported
  }
}
```

**Key points:**
- Always wrap browser APIs in try/catch
- Provide sensible fallback values
- Never let storage failures crash the app

> **Why This Matters**: Fail-safe browser access ensures your application remains robust across different environments (SSR) and browser configurations (Private Mode).

---

## Anti-Patterns to Avoid

### NEVER use mutate()

```typescript
// BAD - mutate is deprecated
this.items.mutate(arr => arr.push(newItem));

// GOOD - use update with spread
this.items.update(arr => [...arr, newItem]);
```

### NEVER use @Input/@Output decorators

```typescript
// BAD - legacy decorators
@Input() userId: string;
@Output() clicked = new EventEmitter<void>();

// GOOD - signal-based
readonly userId = input.required<string>();
readonly clicked = output<void>();
```

### NEVER read signals outside reactive context without purpose

```typescript
// BAD - unnecessary signal read
ngOnInit() {
  console.log(this.user()); // Side effect, not reactive
}

// GOOD - use effect() for side effects
constructor() {
  effect(() => {
    console.log('User changed:', this.user());
  });
}
```
