// BLUEPRINT: Angular reactive form validators
// STRUCTURAL: ValidatorFn factory, cross-field validation, error-preservation pattern, async validator, error message map
// ILLUSTRATIVE: service type (MyService -> your service), regex pattern, error keys, field names

import { AbstractControl, AsyncValidatorFn, ValidatorFn, ValidationErrors } from '@angular/forms';
import { Observable, map, catchError, of } from 'rxjs';

// --- Synchronous validators ---

// STRUCTURAL: factory pattern — returns ValidatorFn for reuse across multiple controls
export function currencyValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value;
    if (!value) return null;
    // ILLUSTRATIVE: replace regex to match your currency format requirements
    const isValid = /^\d+(\.\d{1,2})?$/.test(value);
    return isValid ? null : { currency: { value: control.value } };
  };
}

// STRUCTURAL: cross-field validator — attach to parent FormGroup, not individual control
export const dateRangeValidator: ValidatorFn = (group: AbstractControl): ValidationErrors | null => {
  // ILLUSTRATIVE: replace 'startDate'/'endDate' with your control names
  const start = group.get('startDate')?.value;
  const end = group.get('endDate')?.value;
  return start && end && start > end ? { dateRange: true } : null;
};

// STRUCTURAL: error-preservation pattern — when clearing cross-field errors, never clobber sibling validator errors
export const matchValidator = (controlName: string, matchingControlName: string): ValidatorFn => {
  return (abstractControl: AbstractControl): ValidationErrors | null => {
    const control = abstractControl.get(controlName);
    const matchingControl = abstractControl.get(matchingControlName);
    if (!control || !matchingControl) return null;

    const isMatch = control.value === matchingControl.value;
    const currentErrors = matchingControl.errors;

    if (!isMatch) {
      matchingControl.setErrors({ ...currentErrors, mismatch: true });
      return { mismatch: true };
    }

    if (currentErrors?.['mismatch']) {
      const { mismatch: _, ...remainingErrors } = currentErrors;
      matchingControl.setErrors(Object.keys(remainingErrors).length ? remainingErrors : null);
    }
    return null;
  };
};

// --- Async validators ---

// ILLUSTRATIVE: replace MyService with your duplicate-check service
interface MyService { checkExists(value: unknown): Observable<boolean>; }

// STRUCTURAL: async validator factory — inject service, map result to error or null
export function duplicateCheckValidator(service: MyService): AsyncValidatorFn {
  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    return service.checkExists(control.value).pipe(
      map(exists => (exists ? { exists: true } : null)),
      catchError(() => of(null))
    );
  };
}

// --- Error message mapping ---

interface MinLengthError { requiredLength: number; actualLength: number; }

// STRUCTURAL: typed error map — add entries for every custom validator key you introduce
const ERROR_MESSAGES: Record<string, (err: unknown) => string> = {
  required: () => 'This field is required',
  email: () => 'Invalid email format',
  minlength: (err) => `Minimum ${(err as MinLengthError).requiredLength} characters required`,
  pattern: () => 'Invalid format',
  // ILLUSTRATIVE: add custom keys here: currency, dateRange, mismatch, exists, etc.
};

export function getErrorMessage(errors: ValidationErrors | null): string {
  if (!errors) return '';
  const firstKey = Object.keys(errors)[0];
  return ERROR_MESSAGES[firstKey]?.(errors[firstKey]) ?? 'Invalid field';
}
