# Reference: RBAC Patterns

## Role Hierarchy Patterns

```typescript
export enum Role {
  Admin = 'ADMIN',
  Manager = 'MANAGER',
  Reviewer = 'REVIEWER',
  User = 'USER'
}

export const ROLE_HIERARCHY: Record<Role, Role[]> = {
  [Role.Admin]: [Role.Admin, Role.Manager, Role.Reviewer, Role.User],
  [Role.Manager]: [Role.Manager, Role.Reviewer, Role.User],
  [Role.Reviewer]: [Role.Reviewer, Role.User],
  [Role.User]: [Role.User]
};

export function hasRole(userRole: Role, requiredRole: Role): boolean {
  return ROLE_HIERARCHY[userRole]?.includes(requiredRole) || false;
}
```

## Permission Checking Utilities

```typescript
export interface Permission {
  action: 'create' | 'read' | 'update' | 'delete' | 'approve';
  resource: 'request' | 'vendor' | 'contract';
}

/** Role-to-permission mapping for procurement domain */
const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [Role.Admin]: [
    {action: 'create', resource: 'request'}, {action: 'read', resource: 'request'},
    {action: 'update', resource: 'request'}, {action: 'delete', resource: 'request'},
    {action: 'approve', resource: 'request'}, {action: 'read', resource: 'vendor'},
    {action: 'update', resource: 'vendor'}, {action: 'read', resource: 'contract'},
    {action: 'approve', resource: 'contract'},
  ],
  [Role.Manager]: [
    {action: 'create', resource: 'request'}, {action: 'read', resource: 'request'},
    {action: 'update', resource: 'request'}, {action: 'approve', resource: 'request'},
    {action: 'read', resource: 'vendor'}, {action: 'read', resource: 'contract'},
  ],
  [Role.Reviewer]: [
    {action: 'read', resource: 'request'}, {action: 'read', resource: 'vendor'},
    {action: 'read', resource: 'contract'},
  ],
  [Role.User]: [
    {action: 'create', resource: 'request'}, {action: 'read', resource: 'request'},
  ],
};

@Injectable({providedIn: 'root'})
export class PermissionService {
  canAccess(userRoles: Role[], permission: Permission): boolean {
    return userRoles.some(role => this.checkPermission(role, permission));
  }

  private checkPermission(role: Role, permission: Permission): boolean {
    const allowed = ROLE_PERMISSIONS[role] || [];
    return allowed.some(p => p.action === permission.action && p.resource === permission.resource);
  }
}
```

## Angular Route Guard with Roles

```typescript
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';
import { Role } from './roles';

export const roleGuard = (requiredRoles: Role[]): CanActivateFn => {
  return (route, state) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const userRole = authService.getUserRole();

    if (requiredRoles.includes(userRole)) {
      return true;
    }

    router.navigate(['/unauthorized']);
    return false;
  };
};
```

## Template Directives for Role-Based Visibility

```typescript
import { Directive, TemplateRef, ViewContainerRef, inject, input, effect } from '@angular/core';
import { AuthService } from './auth.service';
import { Role } from './roles';

@Directive({
  selector: '[appHasRole]',
})
export class HasRoleDirective {
  private readonly authService = inject(AuthService);
  private readonly templateRef = inject(TemplateRef<unknown>);
  private readonly viewContainer = inject(ViewContainerRef);

  /** Signal-based input for role requirements */
  readonly appHasRole = input.required<Role | Role[]>();

  constructor() {
    effect(() => {
      const roles = this.appHasRole();
      const requiredRoles = Array.isArray(roles) ? roles : [roles];
      const userRole = this.authService.getUserRole();

      this.viewContainer.clear();
      if (requiredRoles.includes(userRole)) {
        this.viewContainer.createEmbeddedView(this.templateRef);
      }
    });
  }
}

// Usage in template (structural directive syntax):
// <div *appHasRole="['ADMIN', 'MANAGER']">Admin content</div>
```
