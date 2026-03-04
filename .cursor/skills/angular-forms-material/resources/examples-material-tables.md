# Examples: Material Tables

> **Note**: Angular Material table directives (`*matHeaderCellDef`, `*matCellDef`, `*matHeaderRowDef`, `*matRowDef`) are structural directives required by the table component. These are distinct from deprecated `*ngIf`/`*ngFor` directives and cannot be replaced with `@if`/`@for` control flow.

### MatTable with MatSort
Configuring a sortable data table.

```typescript
@Component({ ... })
export class UserTableComponent {
  displayedColumns: string[] = ['id', 'name', 'email', 'role'];
  dataSource = new MatTableDataSource<User>([]);

  @ViewChild(MatSort) sort!: MatSort;

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
  }
}
```

```html
<table mat-table [dataSource]="dataSource" matSort>
  <ng-container matColumnDef="name">
    <th mat-header-cell *matHeaderCellDef mat-sort-header> Name </th>
    <td mat-cell *matCellDef="let user"> {{user.name}} </td>
  </ng-container>

  <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
  <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
</table>
```

### MatPaginator Integration
Adding pagination to the table.

```typescript
@ViewChild(MatPaginator) paginator!: MatPaginator;

ngAfterViewInit() {
  this.dataSource.paginator = this.paginator;
}
```

```html
<mat-paginator [pageSizeOptions]="[5, 10, 25, 100]" aria-label="Select page of users"></mat-paginator>
```

### Row Selection with SelectionModel
Implementing multi-row selection.

```typescript
import { SelectionModel } from '@angular/cdk/collections';

selection = new SelectionModel<User>(true, []);

isAllSelected() {
  const numSelected = this.selection.selected.length;
  const numRows = this.dataSource.data.length;
  return numSelected === numRows;
}

toggleAllRows() {
  if (this.isAllSelected()) {
    this.selection.clear();
    return;
  }
  this.selection.select(...this.dataSource.data);
}
```

### Custom Cell Templates
Conditional styling or buttons in cells.

<!-- @else here is template rendering control flow (visual state), not logic branching. -->
```html
<ng-container matColumnDef="status">
  <th mat-header-cell *matHeaderCellDef> Status </th>
  <td mat-cell *matCellDef="let user">
    @if (user.active) {
      <span class="badge badge-success">Active</span>
    } @else {
      <span class="badge badge-warn">Inactive</span>
    }
  </td>
</ng-container>

<ng-container matColumnDef="actions">
  <th mat-header-cell *matHeaderCellDef> Actions </th>
  <td mat-cell *matCellDef="let user">
    <button mat-icon-button (click)="edit(user)">
      <mat-icon>edit</mat-icon>
    </button>
  </td>
</ng-container>
```

### Loading and Empty States
UI feedback when data is missing or fetching.

```html
<div class="table-container">
  @if (loading()) {
    <div class="loading-shade">
      <mat-spinner></mat-spinner>
    </div>
  }

  <table mat-table ...>...</table>

  @if (dataSource.data.length === 0 && !loading()) {
    <div class="empty-state">
      No records found.
    </div>
  }
</div>
```
