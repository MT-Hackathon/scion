# Examples: Reactive Forms

### Typed FormGroup Creation
Always define an interface for the form structure to ensure type safety.

```typescript
import { FormControl, FormGroup, Validators } from '@angular/forms';

interface ContactForm {
  name: FormControl<string>;
  email: FormControl<string>;
  message: FormControl<string>;
}

const contactForm = new FormGroup<ContactForm>({
  name: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
  message: new FormControl('', { nonNullable: true })
});
```

### Custom Sync Validators
Custom validators should return `ValidatorFn`.

```typescript
import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

// Currency validator
export function currencyValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value;
    if (!value) return null;
    const isValid = /^\d+(\.\d{1,2})?$/.test(value);
    return isValid ? null : { currency: { value: control.value } };
  };
}

// Date range validator (Cross-field)
export const dateRangeValidator: ValidatorFn = (group: AbstractControl): ValidationErrors | null => {
  const start = group.get('startDate')?.value;
  const end = group.get('endDate')?.value;
  return start && end && start > end ? { dateRange: true } : null;
};
```

### Async Validators
Used for backend checks like duplicate verification.

```typescript
import { AbstractControl, AsyncValidatorFn, ValidationErrors } from '@angular/forms';
import { Observable, map, catchError, of, delay } from 'rxjs';

export function duplicateCheckValidator(service: MyService): AsyncValidatorFn {
  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    return service.checkExists(control.value).pipe(
      map(exists => (exists ? { exists: true } : null)),
      catchError(() => of(null))
    );
  };
}
```

### FormArray for Line Items
Dynamic fields handling.

```typescript
import { FormArray, FormControl, NonNullableFormBuilder } from '@angular/forms';

// Component setup
private fb = inject(NonNullableFormBuilder);

form = this.fb.group({
  items: this.fb.array([
    this.fb.group({
      description: [''],
      quantity: [1]
    })
  ])
});

get items() {
  return this.form.controls.items;
}

addItem() {
  this.items.push(this.fb.group({
    description: [''],
    quantity: [1]
  }));
}

removeItem(index: number) {
  this.items.removeAt(index);
}
```

### Form Submission with Loading State
Handle submission with loading flags and error handling.

```typescript
loading = signal(false);

onSubmit() {
  if (this.form.invalid) return;

  this.loading.set(true);
  this.service.save(this.form.getRawValue()).pipe(
    finalize(() => this.loading.set(false))
  ).subscribe({
    next: () => this.toast.success('Saved successfully'),
    error: (err) => this.toast.error('Failed to save')
  });
}
```
