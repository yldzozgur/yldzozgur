---
title: "Default exports break refactoring. Named exports don't."
description: "Default exports let consumers name imports anything they want. This creates invisible coupling that makes renaming and codebase searches unreliable."
pubDate: 2024-01-25
tags: ["JavaScript"]
draft: false
---

Every module bundler and JavaScript environment supports both default and named exports. Most style guides pick one and stick with it. Here is why named exports are the right choice for most code.

## What default exports allow

```js
// math.js
export default function add(a, b) { return a + b; }

// consumer1.js
import add from "./math";

// consumer2.js
import sum from "./math"; // completely different name, same export

// consumer3.js
import please_work from "./math"; // still valid
```

Default exports let every consumer choose their own name. The module does not enforce anything. `add`, `sum`, and `please_work` all import the exact same function.

## Why this breaks refactoring

When you rename `add` to `addition` inside `math.js`, nothing in the consumers breaks because they never imported `add` by name. But the consumers are still calling it `add` or `sum`, and any developer reading the code has to mentally map the local name back to the source file to understand what the function is.

More critically, "find all usages of add" no longer works reliably. If you search for `add` in your codebase, you will miss `sum` and `please_work`. If you search for the file, you find the consumers but not what they call it.

Named exports prevent this:

```js
// math.js
export function add(a, b) { return a + b; }

// consumer.js
import { add } from "./math";
// Cannot be renamed without a deliberate decision
```

Now "find all usages of add" works across the entire codebase. Renaming tools in editors work correctly. The name is consistent everywhere.

## Tree shaking is simpler with named exports

Bundlers like webpack and Rollup can tree-shake both default and named exports, but named exports make it more straightforward. When a module has named exports, the bundler can clearly see which exports are used. With a default export that is an object, the analysis is harder:

```js
// Harder to tree-shake
export default { add, subtract, multiply, divide };

// Easy to tree-shake
export { add, subtract, multiply, divide };
```

In the second case, if only `add` is imported, the bundler can confidently exclude the rest.

## Re-exporting is cleaner

Barrel files (index.js that re-exports from many modules) are common in large codebases. Re-exporting named exports is explicit:

```js
// utils/index.js
export { add, subtract } from "./math";
export { format, parse } from "./dates";
export { capitalize, truncate } from "./strings";
```

Re-exporting default exports requires making up a name:

```js
export { default as add } from "./math";
export { default as format } from "./dates";
// The "default as name" pattern is awkward and easy to get wrong
```

## Autocomplete and discoverability

Named exports are self-documenting. When you type `import { } from "./math"`, your editor can show you every available export from that module. With a default export, you have to know what the module exports, look at the file, or trust documentation.

This matters especially when onboarding to a codebase. Named exports let you see the API surface of a module from any consumer.

## The case for default exports

Default exports make sense in some specific situations:

**React components:** Many teams use default exports for React components because the file name and component name are the same concept. `import Button from "./Button"` reads naturally. However, even here, named exports work fine: `import { Button } from "./Button"`.

**Entry points:** When a module is a single-function utility that does one thing, a default export is not harmful. A module that exports only `add` and nothing else does not benefit much from named export convention.

**Dynamic imports:** `import("./module").then(m => m.default)` works but is slightly more awkward than `import("./module").then(({ specificExport }) => ...)`.

## A practical rule

Prefer named exports everywhere. Use default exports only for React components as a team convention or when a module genuinely exports exactly one thing and will never export more.

If you are working in a codebase that uses both inconsistently, try to be consistent within a file and a feature area. The most expensive part of default exports is not the syntax, it is the loss of searchability and the maintenance burden of multiple names for the same thing.

```js
// Preferred
export function createUser(data) { ... }
export function deleteUser(id) { ... }
export function updateUser(id, data) { ... }

// Avoid
export default {
  create: createUser,
  delete: deleteUser,
  update: updateUser,
};
```

Named exports treat the module as a namespace. Every export has a canonical name. Consumers use that name or use `as` to rename explicitly, which is visible and searchable. That is the right default.
