---
title: "ESLint + Prettier in CI: enforcing style without arguments."
description: "How to configure ESLint and Prettier to work together, and how to run them in CI so style violations block merges."
pubDate: 2025-06-16
tags: ["CI-CD", "Tooling"]
draft: false
---

Style discussions in code review waste time. ESLint and Prettier eliminate them by enforcing rules automatically. Running them in CI makes the rules mandatory.

## What each tool does

**Prettier** handles formatting: indentation, line length, semicolons, quote style, trailing commas. It has almost no configuration options by design. You accept its opinions and stop arguing about formatting.

**ESLint** handles code quality: unused variables, undefined references, incorrect React hook usage, accessibility problems, and anything else a rule can detect. It is highly configurable.

The two tools overlap on some formatting concerns. The standard approach is to disable ESLint formatting rules and let Prettier own formatting entirely.

## Setup

```bash
npm install --save-dev eslint prettier eslint-config-prettier eslint-plugin-react
```

`eslint-config-prettier` turns off all ESLint rules that conflict with Prettier.

Prettier config (`.prettierrc`):

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

ESLint config (`eslint.config.js` for ESLint v9 flat config):

```javascript
import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";
import prettierConfig from "eslint-config-prettier";

export default [
  js.configs.recommended,
  {
    plugins: { react: reactPlugin },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      "no-unused-vars": "error",
      "no-console": "warn",
      "react/prop-types": "off"
    }
  },
  prettierConfig // must be last -- disables conflicting rules
];
```

## Scripts in package.json

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  }
}
```

`prettier --check` exits with code 1 if any file differs from what Prettier would produce. This is the command to run in CI -- it checks without modifying files.

## CI workflow

```yaml
# .github/workflows/lint.yml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - run: npm ci

      - name: Check formatting
        run: npm run format:check

      - name: Run ESLint
        run: npm run lint
```

Both steps must pass for the job to succeed. A formatting violation in a file fails the `format:check` step with output like:

```
[warn] src/components/Button.tsx
[warn] Code style issues found in 1 file. Forgot to run Prettier?
```

An ESLint violation fails the `lint` step:

```
src/utils/auth.js
  12:5  error  'token' is defined but never used  no-unused-vars
```

## Ignoring files

`.prettierignore` and `.eslintignore` (or the `ignores` array in flat config) exclude files from checks:

```
# .prettierignore
dist/
build/
node_modules/
*.min.js
coverage/
```

```javascript
// eslint.config.js
export default [
  { ignores: ["dist/**", "build/**", "coverage/**"] },
  // ... rest of config
];
```

## Pre-commit hooks for local enforcement

Running linting in CI means developers find out about violations only after pushing. Pre-commit hooks catch them before commit:

```bash
npm install --save-dev husky lint-staged
npx husky init
```

`.husky/pre-commit`:

```bash
npx lint-staged
```

`lint-staged` configuration in `package.json`:

```json
{
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{css,json,md}": ["prettier --write"]
  }
}
```

`lint-staged` runs only on staged files, not the whole codebase, keeping pre-commit hooks fast.

## TypeScript type checking

ESLint and Prettier don't check TypeScript types. Add a separate type-check step:

```yaml
- name: TypeScript type check
  run: npx tsc --noEmit
```

This catches type errors without compiling output, and is much faster than a full build.

## The value of consistency

The real benefit of automated style enforcement is not catching bugs. It's eliminating a category of comment from code review entirely. Reviewers stop leaving comments like "should be double quotes" or "missing semicolon" and focus on logic, architecture, and correctness.

It also means every file in the codebase looks like the same person wrote it, which makes reading unfamiliar code faster.

