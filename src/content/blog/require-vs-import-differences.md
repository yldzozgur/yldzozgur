---
title: "require() vs import: they look the same and work completely differently."
description: "CommonJS require() and ES module import are not interchangeable. Understanding the difference explains module compatibility issues and bundler behavior."
pubDate: 2024-03-25
tags: ["JavaScript", "Node.js"]
draft: false
---

`require()` and `import` both load modules, but they are different systems with different semantics. Mixing them incorrectly causes some of the most confusing errors in Node.js and bundled applications.

## CommonJS: require()

CommonJS was Node.js's original module system. It uses `require()` to load modules and `module.exports` to export them.

```js
// math.js
function add(a, b) { return a + b; }
module.exports = { add };

// main.js
const { add } = require("./math");
add(1, 2); // 3
```

Key properties of CommonJS:
- **Synchronous**: `require()` is a regular function call that runs synchronously. It blocks while loading the module.
- **Dynamic**: You can call `require()` anywhere, with any expression: `require(someVariable)`, inside if statements, inside loops.
- **Cached**: After the first load, the module is cached. Every subsequent `require()` of the same path returns the cached exports.

```js
// Dynamic require — valid in CommonJS
const module = condition ? require("./a") : require("./b");
```

## ES Modules: import

ES modules are the standardized module system. Supported natively in browsers and in Node.js with either `.mjs` extension or `"type": "module"` in `package.json`.

```js
// math.js
export function add(a, b) { return a + b; }

// main.js
import { add } from "./math.js";
```

Key properties of ES modules:
- **Asynchronous**: The import system is designed to be asynchronous. Module loading can happen in parallel.
- **Static**: `import` statements must be at the top level. They cannot be inside conditionals or functions. The import graph is resolved before code runs.
- **Live bindings**: Named imports are live bindings to the exported values. If the exporting module changes its exported value, the importing module sees the update.

```js
// This is NOT valid ES module syntax:
if (condition) {
  import something from "./somewhere"; // SyntaxError
}
```

## Dynamic import() — the bridge

ES modules do support dynamic loading through the `import()` function (with parentheses):

```js
const module = await import("./math.js");
module.add(1, 2);

// Or with destructuring:
const { add } = await import("./math.js");
```

`import()` returns a Promise. It is available in both ES module files and CommonJS files, and works in browsers too. Use it for code splitting and conditional loading.

## Interoperability issues

The two systems can work together with caveats.

**In Node.js with CommonJS (default):**
- You can `require()` ES modules only if they export via CommonJS (`module.exports`)
- You cannot `require()` a native `.mjs` file or a package with `"type": "module"` — you get `ERR_REQUIRE_ESM`
- You can use `import()` to load ES modules from CommonJS

**The default export issue:**
When you import a CommonJS module in an ES module context, the entire `module.exports` becomes the default export:

```js
// CommonJS: utils.js
module.exports = { add, subtract };

// ES module import:
import utils from "./utils.js";
utils.add(1, 2); // works

import { add } from "./utils.js"; // may or may not work depending on the bundler/Node version
```

Named exports from CommonJS are sometimes synthesized by bundlers but are not guaranteed in all environments.

## The top-level await difference

ES modules support top-level `await`:

```js
// ES module — valid
const config = await fetchConfig();
export { config };
```

CommonJS does not. Top-level `await` requires ES modules.

## How to know which system you're in

In Node.js:
- `.cjs` files are always CommonJS
- `.mjs` files are always ES modules
- `.js` files follow `"type"` in the nearest `package.json`. Default is CommonJS. Set `"type": "module"` for ES modules.

In TypeScript, you control the output with `"module"` in `tsconfig.json`:
- `"CommonJS"` outputs `require()`
- `"ESNext"` or `"ES2020"` outputs `import`

## Practical advice

For new Node.js projects:
- Use ES modules (`"type": "module"` in `package.json`) and `import/export` everywhere
- Use dynamic `import()` for conditional loading
- Be aware that some packages are CommonJS-only and may require dynamic import

For existing CommonJS projects:
- Stick with `require()` for consistency unless you're migrating
- Use `import()` when you need to load ES-only packages

The friction mostly appears at the boundaries — when a CJS file tries to load an ESM package or vice versa. Knowing which system you're in eliminates most of the confusion.
