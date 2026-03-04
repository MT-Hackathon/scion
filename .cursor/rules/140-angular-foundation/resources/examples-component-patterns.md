# Examples: Angular Component Patterns

Component patterns for Angular 21 with standalone components and signals.

---

## Standalone Component with inject()

```typescript
import {Component, inject} from '@angular/core';
import {MatSidenavModule} from '@angular/material/sidenav';
import {NavigationService} from '@core/services/navigation.service';

@Component({
  selector: 'app-shell',
  imports: [MatSidenavModule],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.scss',
})
export class AppShell {
  readonly navigationService = inject(NavigationService);
}
```

**Key points:**

- No `standalone: true` (default in Angular 21)
- `inject()` in class body, not constructor
- `readonly` for injected services
- `imports` array for dependencies

---

## Service with Signals

```typescript
import {computed, inject, Injectable, signal} from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class NavigationService {
  readonly mobileDetectionService = inject(MobileDetectionService);

  // Private mutable state
  private readonly isMobileNavOpen = signal(false);

  // Public computed (derived state)
  readonly isNavigationOpen = computed(() => {
    if (!this.mobileDetectionService.isMobile()) return true;
    return this.isMobileNavOpen();
  });

  // Methods that update state
  toggleSidenav(): void {
    this.isMobileNavOpen.update((prev) => !prev);
  }
}
```

**Key points:**

- `providedIn: 'root'` for singleton services
- Private signals for internal state
- Public computed for derived state
- `update()` for state changes, not `mutate()`

---

## Component with OnPush

```typescript
import {ChangeDetectionStrategy, Component, signal} from '@angular/core';

@Component({
  selector: 'app-server-status',
  templateUrl: './server-status.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServerStatus {
  readonly isServerRunning = signal(true);

  toggleServerStatus(): void {
    this.isServerRunning.update(running => !running);
  }
}
```

---

## Template with Modern Control Flow

<!-- @else in templates represents visual state branching, not logic control flow.
     The "zero else in logic functions" rule applies to TypeScript/Python code only. -->
```html
<section class="container">
  @if (isServerRunning()) {
    <span>Server is running</span>
  } @else {
    <span>Server is stopped</span>
  }

  @for (item of items(); track item.id) {
    <div class="item">{{ item.name }}</div>
  } @empty {
    <div class="empty-state">No items found</div>
  }

  <button (click)="toggleServerStatus()">Toggle</button>
</section>
```

**Key points:**

- `@if`/`@else` instead of `*ngIf`
- `@for` with `track` instead of `*ngFor` with `trackBy`
- `@empty` block for empty collections

---

## Component with Material Imports

```typescript
import {Component, inject} from '@angular/core';
import {RouterModule} from '@angular/router';
import {MatListModule} from '@angular/material/list';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';
import {NavigationService} from '@core/services/navigation.service';

@Component({
  selector: 'app-side-navigation',
  imports: [
    RouterModule,
    MatListModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './side-navigation.html',
  styleUrl: './side-navigation.scss',
})
export class SideNavigation {
  readonly navigationService = inject(NavigationService);

  protected handleNavigationClick(): void {
    this.navigationService.handleNavigationClick();
  }
}
```

**Key points:**

- Import Material modules directly in component
- `protected` for template-only methods
- `readonly` for injected services
