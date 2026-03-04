# Examples: Service Testing

Patterns for testing Angular services with Vitest and TestBed.

---

## Basic Service Test Setup

```typescript
import {TestBed} from '@angular/core/testing';
import {signal, WritableSignal} from '@angular/core';
import {NavigationService} from './navigation.service';
import {MobileDetectionService} from '@core/services/mobile-detection.service';
import {ProfileService} from '@core/services/profile.service';
import {MockedObject} from 'vitest';

describe('NavigationService', () => {
  let service: NavigationService;
  let mockProfileService: MockedObject<Partial<ProfileService>>;
  let mockMobileDetectionService: MockedObject<Partial<MobileDetectionService>>;

  // Declare at describe scope so individual tests can call .set() on them.
  // Initialize inside beforeEach — fresh signal per test prevents leakage.
  let isMobileSignal: WritableSignal<boolean>;
  let isAuthenticatedSignal: WritableSignal<boolean>;

  beforeEach(() => {
    isMobileSignal = signal(false);
    isAuthenticatedSignal = signal(false);

    // Create mock services with signal properties
    mockProfileService = {
      isAuthenticated: isAuthenticatedSignal,
    };

    mockMobileDetectionService = {
      isMobile: isMobileSignal,
    };

    TestBed.configureTestingModule({
      providers: [
        NavigationService,
        {provide: ProfileService, useValue: mockProfileService},
        {provide: MobileDetectionService, useValue: mockMobileDetectionService},
      ],
    });

    service = TestBed.inject(NavigationService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
```

---

## Testing Computed Signals

```typescript
describe('sidenavMode', () => {
  /**
   * Verifies that sidenav mode is 'side' for desktop view.
   */
  it('should return "side" for desktop view', () => {
    isMobileSignal.set(false);

    expect(service.sidenavMode()).toBe('side');
  });

  /**
   * Verifies that sidenav mode is 'over' for mobile view.
   */
  it('should return "over" for mobile view', () => {
    isMobileSignal.set(true);

    expect(service.sidenavMode()).toBe('over');
  });

  /**
   * Verifies reactive updates when signal changes.
   */
  it('should update reactively when mobile state changes', () => {
    isMobileSignal.set(false);
    expect(service.sidenavMode()).toBe('side');

    isMobileSignal.set(true);
    expect(service.sidenavMode()).toBe('over');

    isMobileSignal.set(false);
    expect(service.sidenavMode()).toBe('side');
  });
});
```

---

## Testing State Toggle Methods

```typescript
describe('toggleSidenav', () => {
  /**
   * Verifies that toggleSidenav switches the navigation open state.
   */
  it('should toggle the mobile navigation open state', () => {
    isMobileSignal.set(true);

    // Initial state
    const initialState = service.isNavigationOpen();

    // Toggle
    service.toggleSidenav();
    expect(service.isNavigationOpen()).toBe(!initialState);

    // Toggle again
    service.toggleSidenav();
    expect(service.isNavigationOpen()).toBe(initialState);
  });
});
```

---

## Testing Conditional Logic

```typescript
describe('isNavigationOpen', () => {
  /**
   * Verifies that navigation is always open on desktop view.
   */
  it('should always return true for desktop view', () => {
    isMobileSignal.set(false);

    expect(service.isNavigationOpen()).toBe(true);
  });

  /**
   * Verifies that navigation state can be toggled on mobile view.
   */
  it('should return mobile nav open state for mobile view', () => {
    isMobileSignal.set(true);

    // Initial state should be closed on mobile
    expect(service.isNavigationOpen()).toBe(false);

    // Toggle to open
    service.toggleSidenav();
    expect(service.isNavigationOpen()).toBe(true);

    // Toggle to close
    service.toggleSidenav();
    expect(service.isNavigationOpen()).toBe(false);
  });
});
```

---

## Testing with TestBed Reset

```typescript
it('should initialize navigation state based on device type', () => {
  // Test with mobile view
  isMobileSignal.set(true);
  const mobileService = TestBed.inject(NavigationService);
  expect(mobileService.isNavigationOpen()).toBe(false);

  // Reset and test with desktop view
  isMobileSignal.set(false);
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    providers: [
      NavigationService,
      {provide: ProfileService, useValue: mockProfileService},
      {provide: MobileDetectionService, useValue: mockMobileDetectionService},
    ],
  });

  const desktopService = TestBed.inject(NavigationService);
  expect(desktopService.isNavigationOpen()).toBe(true);
});
```

---

## Testing Null Safety

```typescript
describe('visibleNavigationItems', () => {
  /**
   * Verifies graceful handling of missing config.
   */
  it('should return empty array if config is undefined', () => {
    const items = service.visibleNavigationItems();

    expect(items).toBeDefined();
    expect(Array.isArray(items)).toBe(true);
  });
});
```
