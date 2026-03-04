# Examples: Component Testing

Patterns for testing Angular components with Vitest and TestBed.

---

## Basic Component Test Setup

```typescript
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {signal} from '@angular/core';
import {MyComponent} from './my.component';
import {MyService} from '@core/services/my.service';

describe('MyComponent', () => {
  let component: MyComponent;
  let fixture: ComponentFixture<MyComponent>;
  let mockService: Partial<MyService>;

  beforeEach(async () => {
    mockService = {
      data: signal([]),
      isLoading: signal(false),
    };

    await TestBed.configureTestingModule({
      imports: [MyComponent],
      providers: [
        {provide: MyService, useValue: mockService},
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

---

## Testing Component with Inputs

```typescript
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {Component, input} from '@angular/core';

// Component under test
@Component({
  selector: 'app-user-card',
  template: `<div>{{ userName() }}</div>`,
})
class UserCard {
  readonly userName = input.required<string>();
}

describe('UserCard', () => {
  let fixture: ComponentFixture<UserCard>;
  let component: UserCard;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserCard],
    }).compileComponents();

    fixture = TestBed.createComponent(UserCard);
    component = fixture.componentInstance;
  });

  it('should display user name', () => {
    // Set input using fixture.componentRef
    fixture.componentRef.setInput('userName', 'John Doe');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('John Doe');
  });
});
```

---

## Testing Component with Outputs

```typescript
describe('AppButton', () => {
  let fixture: ComponentFixture<AppButton>;
  let component: AppButton;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppButton],
    }).compileComponents();

    fixture = TestBed.createComponent(AppButton);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should emit clicked event when button is clicked', () => {
    const clickedSpy = vi.fn();
    component.clicked.subscribe(clickedSpy);

    const button = fixture.nativeElement.querySelector('button');
    button.click();

    expect(clickedSpy).toHaveBeenCalled();
  });
});
```

---

## Testing Template Rendering

```typescript
describe('template rendering', () => {
  it('should show loading state when loading', () => {
    mockService.isLoading = signal(true);
    fixture.detectChanges();

    const spinner = fixture.nativeElement.querySelector('.loading-spinner');
    expect(spinner).toBeTruthy();
  });

  it('should show data when loaded', () => {
    mockService.isLoading = signal(false);
    mockService.data = signal([{id: 1, name: 'Item 1'}]);
    fixture.detectChanges();

    const items = fixture.nativeElement.querySelectorAll('.item');
    expect(items.length).toBe(1);
  });

  it('should show empty state when no data', () => {
    mockService.isLoading = signal(false);
    mockService.data = signal([]);
    fixture.detectChanges();

    const emptyState = fixture.nativeElement.querySelector('.empty-state');
    expect(emptyState).toBeTruthy();
  });
});
```

---

## Testing with Router

```typescript
import {provideRouter} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

describe('NavigationComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavigationComponent],
      providers: [
        provideRouter([
          {path: 'home', component: HomeComponent},
          {path: 'about', component: AboutComponent},
        ]),
      ],
    }).compileComponents();
  });

  it('should navigate to home', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/home');

    expect(harness.routeNativeElement?.textContent).toContain('Home');
  });
});
```

---

## Testing Material Components

```typescript
import {HarnessLoader} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {MatButtonHarness} from '@angular/material/button/testing';

describe('MyComponent with Material', () => {
  let loader: HarnessLoader;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(MyComponent);
    loader = TestbedHarnessEnvironment.loader(fixture);
  });

  it('should click material button', async () => {
    const button = await loader.getHarness(MatButtonHarness);
    await button.click();

    expect(component.wasClicked()).toBe(true);
  });
});
```
