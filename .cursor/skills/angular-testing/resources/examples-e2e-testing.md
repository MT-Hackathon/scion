# Examples: E2E Testing with Playwright

## Playwright Test Setup

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should log in successfully', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Welcome, testuser');
  });
});
```

## Page Object Class

```typescript
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.locator('input[name="username"]');
    this.passwordInput = page.locator('input[name="password"]');
    this.loginButton = page.locator('button[type="submit"]');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(user: string, pass: string) {
    await this.usernameInput.fill(user);
    await this.passwordInput.fill(pass);
    await this.loginButton.click();
  }
}
```

## Common Assertions

```typescript
// Assert element visibility
await expect(page.locator('.sidebar')).toBeVisible();

// Assert text content
await expect(page.locator('.status-badge')).toHaveText('Active');

// Assert attribute value
await expect(page.locator('input[name="email"]')).toHaveValue('user@example.com');

// Assert CSS class
await expect(page.locator('button.submit')).toHaveClass(/btn-primary/);
```

## Form Interaction Testing

```typescript
test('should handle form validation', async ({ page }) => {
  await page.goto('/register');
  
  // Submit without filling
  await page.click('button[type="submit"]');
  
  // Check for error messages
  await expect(page.locator('.error-message')).toBeVisible();
  await expect(page.locator('.error-message')).toContainText('Required');
});
```

## Navigation Testing

```typescript
test('should navigate between pages', async ({ page }) => {
  await page.goto('/');
  
  await page.click('nav >> text=Settings');
  await expect(page).toHaveURL(/\/settings/);
  
  await page.goBack();
  await expect(page).toHaveURL('/');
});
```
