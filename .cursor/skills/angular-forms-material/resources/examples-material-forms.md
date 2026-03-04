# Examples: Material Forms

### MatFormField with Error Messages
Standard pattern for displaying validation errors in Material.

```html
<mat-form-field appearance="outline" class="full-width">
  <mat-label>Username</mat-label>
  <input matInput formControlName="username" placeholder="Enter username">
  <mat-icon matSuffix>person</mat-icon>
  @if (form.get('username')?.hasError('required')) {
    <mat-error>Username is required</mat-error>
  }
  @if (form.get('username')?.hasError('minlength')) {
    <mat-error>Username must be at least 3 characters</mat-error>
  }
  <mat-hint>Choose a unique identifier</mat-hint>
</mat-form-field>
```

### MatSelect with Async Options
Populating dropdowns from an API. Uses `appearance="outline"` for consistency with the border-focused design.

```html
<mat-form-field appearance="outline">
  <mat-label>Department</mat-label>
  <mat-select formControlName="departmentId">
    @for (dept of departments$ | async; track dept.id) {
      <mat-option [value]="dept.id">{{ dept.name }}</mat-option>
    }
  </mat-select>
</mat-form-field>
```

### MatAutocomplete for Typeahead
Implementing search-as-you-type using signals. Uses `appearance="outline"` for consistency.

```typescript
private readonly myControl = new FormControl('', {nonNullable: true});

/** Reactive search results using toSignal for automatic cleanup */
readonly filteredOptions = toSignal(
  this.myControl.valueChanges.pipe(
    startWith(''),
    debounceTime(300),
    switchMap(value => this.service.search(value))
  ),
  {initialValue: []}
);
```

```html
<mat-form-field appearance="outline">
  <mat-label>Search Country</mat-label>
  <input type="text" matInput [formControl]="myControl" [matAutocomplete]="auto">
  <mat-autocomplete #auto="matAutocomplete">
    @for (option of filteredOptions(); track option) {
      <mat-option [value]="option">{{ option }}</mat-option>
    }
  </mat-autocomplete>
</mat-form-field>
```

### MatDatepicker Usage
Standard date picking configuration with `appearance="outline"`.

```html
<mat-form-field appearance="outline">
  <mat-label>Choose a date</mat-label>
  <input matInput [matDatepicker]="picker" formControlName="expiryDate">
  <mat-hint>MM/DD/YYYY</mat-hint>
  <mat-datepicker-toggle matIconSuffix [for]="picker"></mat-datepicker-toggle>
  <mat-datepicker #picker></mat-datepicker>
</mat-form-field>
```

### Form Layout Patterns
#### Field Grid (within a section card) — Use `app-field-grid` for responsive form fields within a card. Fields auto-fit into columns.
```html
<div class="app-section-card" [formGroup]="myForm">
  <h3>Section Title</h3>
  <div class="app-field-grid">
    <mat-form-field appearance="outline">
      <mat-label>First Name</mat-label>
      <input matInput formControlName="firstName">
    </mat-form-field>
    <mat-form-field appearance="outline">
      <mat-label>Last Name</mat-label>
      <input matInput formControlName="lastName">
    </mat-form-field>
    <mat-form-field appearance="outline" class="app-span-full">
      <mat-label>Description</mat-label>
      <textarea matInput formControlName="description"></textarea>
    </mat-form-field>
  </div>
</div>
```
#### Multi-Column Form Layout — Use `app-form-columns` / `app-form-column` for side-by-side section cards. Cards size independently (no linked row heights). Collapses to single column on mobile.
```html
<form [formGroup]="myForm" class="app-form-columns">
  <div class="app-form-column">
    <div class="app-section-card">...</div>
    <div class="app-section-card">...</div>
  </div>
  <div class="app-form-column">
    <div class="app-section-card">...</div>
    <div class="app-section-card">...</div>
  </div>
</form>
```
**Why Flexbox, not CSS Grid?** Grid's default `align-items: stretch` links row heights across columns — expanding content in one column creates gaps in the other. Flexbox columns are independent.
