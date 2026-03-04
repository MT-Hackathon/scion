# Reference: Behavioral Testing Patterns

Guide for writing behavioral tests that support Test-Driven Development (TDD) in Angular. Focus on WHAT a component does rather than HOW it is rendered.

---

## The Problem with Structural Tests

Structural tests rely on the internal implementation details of a component's template. They are fragile and cannot be written before the component exists.

- **Premature Selector Dependency**: You can't write `querySelector('.my-class')` before the template exists.
- **Material Wrapper Complexity**: Angular Material components often add unpredictable wrapper elements that break CSS selectors.
- **Implementation Leakage**: CSS class names and DOM nesting are implementation details that should be free to change without breaking tests.

## Behavioral Testing Philosophy

Behavioral tests define the **contract** of the component. By focusing on inputs, outputs, and state, you can specify component behavior *before* writing a single line of HTML.

- **Test WHAT, not HOW**: Focus on inputs, outputs, state changes, and side effects.
- **TDD Friendly**: These tests can be written against a component class stub.
- **Refactor Safe**: Since they don't depend on the DOM structure, you can refactor the template without breaking the tests.

---

## Patterns with Examples

### Input Contracts
Define how the component processes data passed from its parent.

```typescript
it('should display item name when provided', () => {
  // Setup: Set input using the signal-based API or component instance
  fixture.componentRef.setInput('itemName', 'Test Item');
  fixture.detectChanges();

  // Assert: Check the public state of the component
  expect(component.displayName()).toBe('Test Item');
});
```

### Output Contracts
Verify that the component emits the correct events under specific conditions.

```typescript
it('should emit save event with form data when valid', () => {
  const spy = vi.fn();
  component.saved.subscribe(spy);

  // Act: Set state and trigger action
  component.form.patchValue({ name: 'Valid' });
  component.onSave();

  // Assert: Verify the event was emitted with correct data
  expect(spy).toHaveBeenCalledWith({ name: 'Valid' });
});
```

### Signal Behavior
Specify computed state logic and derived values.

```typescript
it('should compute total from quantity and price', () => {
  // Act: Update source signals
  component.quantity.set(5);
  component.unitPrice.set(100);

  // Assert: Verify derived computed signal
  expect(component.total()).toBe(500);
});
```

### Form Validation
Document the validation rules for the component's internal forms.

```typescript
it('should require email field', () => {
  // Act: Set invalid state
  component.form.patchValue({ email: '' });

  // Assert: Check validation state directly on the form object
  expect(component.form.get('email')?.hasError('required')).toBe(true);
});
```

### Conditional State
Define the logic for showing/hiding content or changing UI states based on signals.

```typescript
it('should show loading state while fetching', () => {
  // Setup: Inject or mock the loading signal source
  loadingSignal.set(true);

  // Assert: Verify the component's internal state reflects the source
  expect(component.isLoading()).toBe(true);
});
```

---

## What NOT to Test First

These should only be tested retrospectively or during the "Refactor" phase of TDD:

- **Exact CSS Classes**: Classes are for styling, not behavior.
- **DOM Structure/Nesting**: Div wrappers and hierarchy are implementation details.
- **Material Internal Structure**: Never test selectors like `.mat-mdc-form-field-infix`.
- **Animation States**: CSS transitions and animations are visual polish.

---

## The TDD Component Workflow

1.  **Define Behavioral Tests**: Write tests defining inputs, outputs, and internal state logic.
2.  **Create Minimal Stub**: Create a component class with just enough properties and methods to compile.
3.  **Green**: Implement the logic (Signals, Effects, Methods) to pass the tests.
4.  **Add Template**: Now that the state is verified, bind it to the HTML template.
5.  **Add Structural Tests (Optional)**: If specific DOM elements are critical (e.g., accessibility labels), add them now.
