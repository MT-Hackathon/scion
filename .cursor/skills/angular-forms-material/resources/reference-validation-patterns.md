# Reference: Validation Patterns

### Built-in Validators
Commonly used validators from `@angular/forms`.

- `Validators.required`: Control must have a non-empty value.
- `Validators.requiredTrue`: Control value must be `true` (e.g. checkbox).
- `Validators.email`: Value must be a valid email format.
- `Validators.minLength(n)`: Value must have at least `n` characters.
- `Validators.maxLength(n)`: Value must have at most `n` characters.
- `Validators.pattern(regex)`: Value must match the provided regex.
- `Validators.min(n)`: Numeric value must be at least `n`.
- `Validators.max(n)`: Numeric value must be at most `n`.

### Custom Validator Signatures
The standard shape for synchronous and asynchronous validators.

**Synchronous:**

```typescript
type ValidatorFn = (control: AbstractControl) => ValidationErrors | null;
```

**Asynchronous:**

```typescript
type AsyncValidatorFn = (control: AbstractControl) => Observable<ValidationErrors | null> | Promise<ValidationErrors | null>;
```

### Cross-Field Validation
Validating values that depend on each other (e.g., password matching).

**Important**: When clearing cross-field errors, preserve other validators' errors.

```typescript
export const matchValidator = (controlName: string, matchingControlName: string): ValidatorFn => {
  return (abstractControl: AbstractControl): ValidationErrors | null => {
    const control = abstractControl.get(controlName);
    const matchingControl = abstractControl.get(matchingControlName);

    if (!control || !matchingControl) return null;

    const isMatch = control.value === matchingControl.value;
    const currentErrors = matchingControl.errors;

    if (!isMatch) {
      // Add mismatch error while preserving existing errors
      matchingControl.setErrors({...currentErrors, mismatch: true});
      return {mismatch: true};
    }

    // Remove only the mismatch error, preserve others
    if (currentErrors?.['mismatch']) {
      const {mismatch, ...remainingErrors} = currentErrors;
      matchingControl.setErrors(Object.keys(remainingErrors).length ? remainingErrors : null);
    }
    return null;
  };
};
```

### Error Message Mapping
Consistent error message handling in templates.

```typescript
interface MinLengthError {
  requiredLength: number;
  actualLength: number;
}

const ERROR_MESSAGES: Record<string, (err: unknown) => string> = {
  required: () => 'This field is required',
  email: () => 'Invalid email format',
  minlength: (err) => `Minimum ${(err as MinLengthError).requiredLength} characters required`,
  pattern: () => 'Invalid format',
};

getErrorMessage(controlName: string): string {
  const control = this.form.get(controlName);
  if (!control?.errors) return '';
  
  const firstErrorKey = Object.keys(control.errors)[0];
  const errorValue = control.errors[firstErrorKey];
  return ERROR_MESSAGES[firstErrorKey]?.(errorValue) ?? 'Invalid field';
}
```
