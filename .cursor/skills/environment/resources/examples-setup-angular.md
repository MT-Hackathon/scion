# Examples: Angular Environment Setup

Angular and Node.js environment setup patterns.

---

## Node.js Setup

### Initial Setup

**Windows**: Install [nvm-windows](https://github.com/coreybutler/nvm-windows).
**Linux/macOS**: Install [nvm](https://github.com/nvm-sh/nvm).

```bash
# Install and use Node.js 22
nvm install 22
nvm use 22

# Verify
node --version  # v22.x.x
npm --version   # 10.x.x
```

### Project Setup

```bash
cd "C:\Users\cmb115\projects\procurement-web"
nvm use 22
npm install
```

---

## Angular CLI

### Global Installation

```bash
npm install -g @angular/cli
ng version
```

### Common Commands

```bash
# Development server
npm start

# Build for production
ng build

# Run tests
npm test

# Generate component
ng generate component features/my-feature
```

---

## VS Code Configuration

### Recommended Extensions

- Angular Language Service
- ESLint
- Prettier
- EditorConfig

### settings.json

```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

---

## Path Aliases

### tsconfig.json

```json
{
  "compilerOptions": {
    "paths": {
      "@core/*": ["src/app/core/*"],
      "@env/*": ["src/environments/*"],
      "@features/*": ["src/app/features/*"]
    }
  }
}
```

### Usage

```typescript
import { NavigationService } from '@core/services/navigation.service';
import { environment } from '@env/environment';
```
