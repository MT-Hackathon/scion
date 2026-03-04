# Examples: Service Orchestration

Service orchestration patterns for Angular 21 state-first architecture.

---

## State Machines with Signals

Using `ThresholdService` as a prime example of a robust state machine implemented with Angular signals.

```typescript:src/app/core/threshold/threshold.service.ts
@Injectable({
  providedIn: 'root',
})
export class ThresholdService {
  private readonly notifications = inject(NotificationService);
  private readonly configurationSignal = signal<ThresholdConfig>(DEFAULT_THRESHOLD_CONFIG);
  private readonly stateSignal = signal<ThresholdState>(createEmptyState(0));
  private readonly dismissedKeySignal = signal<string | null>(null);

  /** Signal-based state exposure */
  readonly state = computed(() => this.stateSignal());
  
  /** Computed readonly accessors for derived state */
  readonly dismissed = computed(() => {
    const key = computeDismissKey(this.stateSignal());
    return this.dismissedKeySignal() === key;
  });

  /** State transitions through dedicated methods */
  updateTotalContractValue(totalContractValue: number): void {
    // ... validation ...
    const nextState = evaluateTotalContractValue(totalContractValue, this.configurationSignal());
    this.applyStateUpdate(nextState, true);
  }

  /** Toast notification deduplication logic */
  private handleToast(state: ThresholdState): void {
    if (this.resetToastEligibilityIfNeeded(state)) {
      return;
    }
    if (!this.isToastEligibleForState(state)) {
      this.lastSeverity = state.severity;
      return;
    }
    // Only send notification if eligibility criteria are met
    if (this.sendToastNotification(state)) {
      this.toastEligible = false;
      this.lastSeverity = state.severity;
    }
  }
}
```

> **Why This Matters**: Encapsulating state within private signals and exposing only computed read-only views prevents external modification of the service's internal state. Centralizing state transitions in dedicated methods ensures that all side effects (like notifications) are consistently applied.

---

## Pure Functions for Domain Logic

Moving complex logic into pure functions outside the class makes the service thin and the logic highly testable.

```typescript:src/app/core/threshold/threshold.service.ts
/** Deterministic state resolution */
const resolveSeverity = (isApproaching: boolean, isExceeding: boolean): ThresholdSeverity => {
  if (isExceeding) return 'error';
  if (isApproaching) return 'warning';
  return 'none';
};

/** Evaluates state against configuration */
const evaluateTotalContractValue = (
  totalContractValue: number,
  configuration: ThresholdConfig,
): ThresholdState => {
  const obppState = evaluateEntry(totalContractValue, 'obpp', configuration.obpp);
  const agencyState = evaluateEntry(totalContractValue, 'agency', configuration.agency);
  return pickMostSevereState(totalContractValue, obppState, agencyState);
};

/** Comparison logic for state prioritization */
const pickMostSevereState = (
  totalContractValue: number,
  obppState: ThresholdState,
  agencyState: ThresholdState,
): ThresholdState => {
  if (obppState.severity === 'none' && agencyState.severity === 'none') {
    return createEmptyState(totalContractValue);
  }

  const comparison = compareSeverity(agencyState.severity, obppState.severity);
  if (comparison > 0) return agencyState;
  if (comparison < 0) return obppState;

  return agencyState.severity === 'none' ? obppState : agencyState;
};
```

> **Why This Matters**: Pure functions are predictable, have no side effects, and can be tested in isolation without setting up Angular's dependency injection container. This separation of concerns keeps the service focused on orchestration.

---

## Defensive Service Patterns

Services should proactively validate inputs to prevent invalid states or runtime errors.

```typescript:src/app/core/threshold/threshold.service.ts
updateTotalContractValue(totalContractValue: number): void {
  /** Early validation with guard clauses */
  if (!Number.isFinite(totalContractValue)) {
    return; // Silent failure for invalid inputs
  }
  if (totalContractValue < 0) {
    return;
  }

  const nextState = evaluateTotalContractValue(totalContractValue, this.configurationSignal());
  this.applyStateUpdate(nextState, true);
}
```

> **Why This Matters**: Guard clauses and finite checks ensure that the service logic only operates on valid data, preventing "garbage-in-garbage-out" scenarios and eliminating the need for complex error handling in callers.

---

## Browser API Guardrails

When interacting with browser APIs that can fail (e.g., in SSR or Private Mode), use protective wrappers.

> **Cross-reference**: For additional browser API patterns in component context, see [Examples: Signal Patterns](examples-signal-patterns.md#safe-browser-api-access-patterns).

```typescript:src/app/core/services/theme.service.ts
/** Safe localStorage access with try/catch */
private readStoredPreference(): boolean | null {
  try {
    const raw = window.localStorage.getItem(ThemeService.STORAGE_KEY);
    if (raw === null) return null;
    return raw === 'true';
  } catch {
    return null; // Fallback when API is unavailable
  }
}

/** Safe window.matchMedia access */
private getSystemPrefersDark(): boolean {
  try {
    return !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch {
    return false; // Fallback for SSR/non-browser environments
  }
}
```

---

## Orchestration vs Data Services

Orchestration services coordinate state from multiple sources, while data services focus on retrieval and persistence.

```typescript:src/app/core/services/navigation.service.ts
@Injectable({
  providedIn: 'root',
})
export class NavigationService {
  /** Orchestration service injects multiple domain/data services */
  readonly profileService = inject(ProfileService);
  readonly mobileDetectionService = inject(MobileDetectionService);

  /** Computed signals derive state from injected services */
  readonly sidenavMode = computed(() => {
    if (this.mobileDetectionService.isMobile()) return 'over';
    return 'side';
  });

  readonly isNavigationOpen = computed(() => {
    if (!this.mobileDetectionService.isMobile()) return true;
    return this.isMobileNavOpen(); // Local state combined with external state
  });
}
```

> **Why This Matters**: Clear separation prevents services from becoming bloated. `NavigationService` doesn't need to know *how* mobile detection works or *how* profile state is fetched; it only needs to know how to *react* to them.
