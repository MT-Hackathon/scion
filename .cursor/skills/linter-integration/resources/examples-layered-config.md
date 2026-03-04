# Examples: Layered Config

How to set up base team config + personal stricter overlay.

---

## Pattern Overview

```
project/
├── eslint.config.js        # Team config (committed)
├── eslint.config.local.js  # Personal overlay (gitignored)
├── .gitignore              # Contains: eslint.config.local.js
└── package.json            # Scripts for both configs
```

---

## TypeScript/Angular Example

### Team Config (eslint.config.js)

```javascript
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import angular from '@angular-eslint/eslint-plugin';
import angularTemplateParser from '@angular-eslint/template-parser';
import globals from 'globals';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  
  // Global ignores
  {
    ignores: ['dist/', 'node_modules/', '.angular/']
  },

  // TypeScript files
  {
    files: ['**/*.ts'],
    plugins: {
      '@angular-eslint': angular
    },
    rules: {
      ...angular.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_'
      }],
      '@typescript-eslint/no-explicit-any': 'warn'
    }
  },

  // HTML templates
  {
    files: ['**/*.html'],
    languageOptions: {
      parser: angularTemplateParser
    },
    plugins: {
      '@angular-eslint': angular
    },
    rules: {
      ...angular.configs.templateRecommended.rules,
      ...angular.configs.templateAccessibility.rules
    }
  }
);
```

### Personal Overlay (eslint.config.local.js)

```javascript
/**
 * Personal ESLint Config - Stricter AI-Optimized Rules
 * 
 * This file is gitignored and extends the team config with
 * additional rules that catch common AI-generated code issues.
 */
import baseConfig from './eslint.config.js';

export default [
  ...baseConfig,
  
  // Stricter rules for AI-assisted development
  {
    files: ['**/*.ts'],
    rules: {
      // Catch magic numbers - AI loves unexplained literals
      '@typescript-eslint/no-magic-numbers': ['warn', {
        ignore: [0, 1, -1, 2, 10, 100],
        ignoreEnums: true,
        ignoreNumericLiteralTypes: true,
        enforceConst: true,
        ignoreReadonlyClassProperties: true,
        ignoreDefaultValues: true
      }],
      
      // No debug code in production
      'no-console': 'warn',
      
      // Catch incomplete work
      'no-warning-comments': ['warn', { 
        terms: ['TODO', 'FIXME', 'HACK', 'XXX'],
        location: 'start'
      }],
      
      // Stricter any handling
      '@typescript-eslint/no-explicit-any': 'error',
      
      // Warn on non-null assertions
      '@typescript-eslint/no-non-null-assertion': 'warn'
    }
  },
  
  // Relax magic numbers in test files
  {
    files: ['**/*.spec.ts', '**/*.test.ts'],
    rules: {
      '@typescript-eslint/no-magic-numbers': 'off'
    }
  }
];
```

---

## Python Example (Ruff)

### Team Config (ruff.toml)

```toml
target-version = "py312"
line-length = 100

exclude = [
  ".git",
  ".venv",
  "__pycache__",
  "build",
  "dist",
]

[lint]
select = [
  "E",      # pycodestyle errors
  "W",      # pycodestyle warnings  
  "F",      # Pyflakes
  "I",      # isort
  "B",      # flake8-bugbear
]

ignore = [
  "E501",   # Line too long - handled by formatter
]

[format]
quote-style = "double"
indent-style = "space"
```

### Personal Overlay (ruff.local.toml)

```toml
# Extends team config with stricter rules
extend = "ruff.toml"

[lint]
extend-select = [
  "T20",    # flake8-print (no print statements)
  "SIM",    # flake8-simplify
  "C4",     # flake8-comprehensions
  "RUF",    # Ruff-specific rules
  "UP",     # pyupgrade
]
```

---

## package.json Scripts

```json
{
  "scripts": {
    "lint": "eslint src/",
    "lint:strict": "eslint --config eslint.config.local.js src/",
    "lint:fix": "eslint src/ --fix",
    "lint:strict:fix": "eslint --config eslint.config.local.js src/ --fix"
  }
}
```

---

## .gitignore Entry

```gitignore
# Personal linter config (stricter than team standards)
eslint.config.local.js
ruff.local.toml
```

---

## Usage in AI Workflow

**Step 1: Check for personal config**

```bash
ls eslint.config.local.js 2>/dev/null && echo "Personal config exists"
```

**Step 2: Run appropriate linter**

```bash
# If personal config exists
npm run lint:strict

# Otherwise
npm run lint
```

**Step 3: Report what ran**
When personal config is used, mention it:
> "Ran strict linting with magic numbers, no-console, and TODO detection enabled."

---

## Syncing Configs

When team config changes, personal overlay automatically inherits changes through the spread operator. No manual sync needed.

If team adds a rule that conflicts with your overlay:

1. The overlay rule takes precedence
2. Verify if team rule is sufficient
3. Remove from overlay if redundant
