---
title: "V8 internals: JIT compilation and what deoptimizes your hot paths."
description: "How V8 moves from interpreted bytecode to optimized machine code, and the specific conditions that cause it to throw that work away."
pubDate: 2026-01-29
tags: ["Architecture"]
draft: false
---

V8 doesn't compile JavaScript to machine code once and call it done. It runs code through multiple tiers of execution, promoting hot code to higher optimization tiers and demoting it back when its assumptions prove wrong. Understanding this pipeline helps you write code that stays in the fast tier.

## The execution pipeline

**Ignition (interpreter):** When V8 first encounters a function, it compiles it to bytecode and runs it in the Ignition interpreter. This is fast to start but slow to execute -- each bytecode instruction is interpreted.

**Feedback vectors:** As Ignition runs bytecode, it records "feedback" about each operation: what types were seen at this call site, what shapes objects had, whether an array was packed or sparse. This profiling data drives later optimization.

**Sparkplug (baseline compiler):** After a function has been called a few times, V8 compiles it with Sparkplug, a fast non-optimizing compiler. This produces machine code directly from bytecode without analysis. It's faster to compile than Maglev/TurboFan and faster to execute than interpretation.

**Maglev (mid-tier JIT):** After more calls, V8 promotes hot functions to Maglev. This uses the feedback data to make type-specialized assumptions. If the feedback says this property is always a Smi (small integer), Maglev generates code that assumes it.

**TurboFan (optimizing JIT):** The highest tier. TurboFan performs aggressive inlining, loop unrolling, escape analysis, and other classical compiler optimizations. Compiling with TurboFan takes time, so it's reserved for the hottest functions.

## What deoptimization is

When optimized code makes an assumption that proves wrong, V8 must **deoptimize**: throw away the optimized machine code and fall back to interpreted execution. If the function continues to be called, it will eventually be re-optimized -- but with updated feedback that reflects what actually happened.

Frequent deoptimizations are expensive: compiling takes CPU time, and the function runs slowly while waiting for re-optimization.

## The conditions that cause deoptimization

**Type changes after optimization:**

```javascript
function add(a, b) {
  return a + b;
}

// Called many times with numbers -- V8 optimizes for numbers
for (let i = 0; i < 10000; i++) add(i, i);

// Now called with a string -- assumption violated, deoptimize
add("hello", "world");
```

**Out-of-bounds array access:**

```javascript
function getItem(arr, i) {
  return arr[i];
}

// Optimized assuming i is always in bounds
// Called with i >= arr.length: deoptimize
```

**Changing array element types:**

V8 tracks the "elements kind" of arrays. A `[1, 2, 3]` array has `PACKED_SMI_ELEMENTS`. Add a float and it becomes `PACKED_DOUBLE_ELEMENTS`. Add an object and it becomes `PACKED_ELEMENTS`. Each transition means the optimized code's assumptions are wrong.

```javascript
const arr = [1, 2, 3];            // PACKED_SMI_ELEMENTS
arr.push(1.5);                     // -> PACKED_DOUBLE_ELEMENTS
arr.push({ x: 1 });               // -> PACKED_ELEMENTS
// Each transition degrades performance
```

**Arguments object:**

Using `arguments` in a function prevents certain optimizations:

```javascript
// Slower: prevents optimization in some cases
function sum() {
  let total = 0;
  for (let i = 0; i < arguments.length; i++) total += arguments[i];
  return total;
}

// Faster: rest parameters are fine
function sum(...nums) {
  return nums.reduce((a, b) => a + b, 0);
}
```

**Try-catch blocks:**

Code inside `try` blocks has historically limited TurboFan's ability to optimize. This has improved in recent V8 versions, but moving `try-catch` outside hot loops is still worth doing:

```javascript
// Worse: try-catch inside hot loop
function processAll(items) {
  return items.map(item => {
    try {
      return transform(item);
    } catch (e) {
      return null;
    }
  });
}

// Better: move error handling outside
function processAll(items) {
  try {
    return items.map(transform);
  } catch (e) {
    return null;
  }
}
```

## Seeing what V8 is doing

In Node.js, you can get optimization information:

```bash
# See which functions get optimized/deoptimized
node --trace-opt --trace-deopt script.js

# Generate a v8.log for analysis
node --prof script.js
node --prof-process isolate-*.log
```

The `--prof-process` output shows which functions are consuming time and whether they're running in optimized or unoptimized code.

In Chrome, the Performance panel's "JavaScript" flame chart shows `[js]` vs `[optimized]` frames. V8's `%GetOptimizationStatus()` intrinsic (available with `--allow-natives-syntax`) lets you check the optimization status of a function from test code.

The pattern is always the same: write code with stable types, stable object shapes, and predictable control flow. V8 is good at optimizing code that looks like it could have been written in a statically typed language.
