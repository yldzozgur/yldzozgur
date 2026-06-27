---
title: "Tree shaking: why your bundle is larger than it should be."
description: "What tree shaking is, how it works, what breaks it, and how to verify it's actually happening in your build."
pubDate: 2025-09-25
tags: ["DevOps"]
draft: false
---

Tree shaking is the process by which a bundler removes unused code from your JavaScript bundle. When it works correctly, importing one function from a library that has 200 functions includes only that one function in your output. When it fails, you ship the entire library even though you used 3% of it.

## How tree shaking works

Tree shaking relies on static analysis of ES module imports and exports. ES modules (`import`/`export`) are statically analyzable - the bundler can determine at build time exactly which exports are used without executing the code.

```javascript
// math.js
export function add(a, b) { return a + b; }
export function subtract(a, b) { return a - b; }
export function multiply(a, b) { return a * b; }
export function divide(a, b) { return a / b; }

// app.js
import { add } from './math.js';
console.log(add(1, 2));
```

The bundler sees that only `add` is imported. It marks `subtract`, `multiply`, and `divide` as unused and excludes them from the bundle. If each function is 1KB, you ship 1KB instead of 4KB.

CommonJS (`require()`) cannot be tree-shaken because it is dynamic:

```javascript
// CommonJS: bundler cannot statically determine what is imported
const math = require('./math');
math[someVariable](); // Could be any export
```

## What breaks tree shaking

**Side effects.** If a module has side effects when imported (code that runs at the module level, not just defines functions), the bundler cannot safely remove it even if none of its exports are used.

```javascript
// This file has a side effect: it registers something globally on import
window.MyPlugin = { ... };

export function helper() { ... }
```

If you import `helper` but not the side effect, the bundler might include the entire module to preserve the side effect.

Mark packages without side effects in `package.json`:

```json
{
  "name": "my-library",
  "sideEffects": false
}
```

For libraries with some side-effecting files (like CSS imports):

```json
{
  "sideEffects": ["*.css", "polyfills.js"]
}
```

This tells bundlers like Webpack and Rollup that any other file can be safely dropped if unused.

**Barrel files.** An index file that re-exports everything from a directory is a common pattern that breaks tree shaking:

```javascript
// components/index.js - barrel file
export { Button } from './Button';
export { Modal } from './Modal';
export { Table } from './Table';
// ... 50 more components
```

```javascript
// Importing from the barrel
import { Button } from '@/components';
```

In theory, bundlers should tree-shake the unused exports. In practice, if any of the re-exported modules have side effects, the entire barrel is included. Large barrel files from UI libraries (Material UI, Ant Design) are a common source of bloat.

Fix: import directly from the source file:

```javascript
// Direct import: definitely tree-shaken
import { Button } from '@/components/Button';
```

Or use babel-plugin-transform-imports to rewrite barrel imports to direct imports at build time.

**CommonJS libraries.** If you import from a library that only ships CommonJS, it cannot be tree-shaken. The entire library is bundled. Check whether the library ships an ESM version (`"module"` or `"exports"` field in package.json).

## Verifying tree shaking

Use `webpack-bundle-analyzer` or `rollup-plugin-visualizer` to see what is in your bundle:

```bash
npm install --save-dev webpack-bundle-analyzer

# In webpack.config.js
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [new BundleAnalyzerPlugin()]
};
```

This generates a visual treemap of your bundle. Large sections from libraries where you use only a small fraction are candidates for investigation.

Check for duplicate packages:

```bash
npx duplicate-package-checker-webpack-plugin
```

Multiple versions of the same package included in one bundle is another common source of bloat.

## Named vs default imports

Named imports are tree-shakeable because the bundler knows exactly what to include:

```javascript
import { debounce } from 'lodash-es'; // Only debounce
```

Default imports can be tree-shaken if the library is written to support it, but some common patterns defeat it:

```javascript
import _ from 'lodash'; // Usually includes all of lodash
_.debounce(...)
```

Lodash-es (the ES module version of lodash) supports per-function tree shaking. The original lodash does not. Switching from `lodash` to `lodash-es` can reduce bundle size by hundreds of kilobytes for applications that use a few utilities.

Tree shaking is automatic when conditions are met. The work is ensuring those conditions hold: ES modules, `sideEffects: false` in package.json, direct imports instead of barrels, and ESM-shipping versions of your dependencies.
