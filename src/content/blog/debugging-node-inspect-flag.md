---
title: "Debugging Node: the --inspect flag and when console.log is the last resort."
description: "Node.js has a full debugger accessible from Chrome DevTools. --inspect gives you breakpoints, call stacks, and memory inspection."
pubDate: 2024-04-22
tags: ["Node.js"]
draft: false
---

`console.log` debugging works, but it scales badly. Adding log statements, re-running, removing them, adding more — it is slow. Node.js has a built-in debugging protocol that connects to Chrome DevTools and gives you breakpoints, call stacks, variable inspection, and memory profiling.

## Starting the debugger

```bash
node --inspect app.js
# Debugger listening on ws://127.0.0.1:9229/...
# Open chrome://inspect in Chrome
```

Or to pause immediately on the first line:

```bash
node --inspect-brk app.js
```

`--inspect-brk` is useful when the bug is in startup code that runs before you could set a breakpoint.

## Connecting in Chrome

1. Open Chrome and navigate to `chrome://inspect`
2. Under "Remote Target" you will see your Node process
3. Click "inspect" to open DevTools

You now have the full Chrome DevTools interface connected to your Node process.

## Breakpoints

In the Sources tab of DevTools, you can open your source files and click line numbers to set breakpoints. Execution pauses when that line is reached. You can then:
- Inspect the current value of any variable
- Step through code line by line
- Step into or over function calls
- View the full call stack

This is significantly faster than adding `console.log` statements because you see the state of all variables at once.

## debugger statement

You can trigger a breakpoint from code:

```js
function processOrder(order) {
  debugger; // execution pauses here when --inspect is active
  const total = calculateTotal(order.items);
  return total;
}
```

The `debugger` statement is ignored when the process is not running with `--inspect`. Add it to code you want to inspect, connect DevTools, trigger the code path, and the execution pauses.

Remove `debugger` statements before committing — they are not harmful in production but indicate unfinished debugging work.

## VS Code debugging

VS Code has built-in Node.js debugging without a browser. Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "node",
      "request": "launch",
      "name": "Launch app",
      "program": "${workspaceFolder}/src/app.js",
      "env": {
        "NODE_ENV": "development"
      }
    },
    {
      "type": "node",
      "request": "attach",
      "name": "Attach to running process",
      "port": 9229
    }
  ]
}
```

The "attach" configuration connects to a process already running with `--inspect`. Useful for debugging in Docker or when the process is started externally.

## Debugging with nodemon

In development, you often want to restart on file changes and debug simultaneously:

```bash
nodemon --inspect app.js
```

When nodemon restarts the process, it keeps the same debug port and Chrome DevTools reconnects automatically.

## Conditional breakpoints

In DevTools, right-click a line number to set a conditional breakpoint. It only pauses when the condition is true:

```
order.total > 1000
```

This avoids pausing on every iteration of a loop and only triggers when the case you care about occurs.

## The console in DevTools

The console in Chrome DevTools, when connected to a Node process, runs code in the Node process. You can call functions, inspect objects, and modify state:

```js
// In the DevTools console while paused at a breakpoint:
order.items.length // inspect a variable
processOrder({ items: [] }) // call a function
require("./utils").format(someValue) // use your code
```

## Memory inspection

In the Memory tab, you can take heap snapshots and compare them. This is how you track down memory leaks — take a snapshot before and after a suspected leak, compare the two to see which objects were retained.

```js
// Force garbage collection to get a clean snapshot
// Start node with: node --inspect --expose-gc app.js
global.gc(); // then take snapshot
```

## When console.log is correct

The debugger is not always faster. `console.log` is appropriate when:
- The bug only manifests in production where you cannot run `--inspect`
- You need to see values over time (a time-series log rather than a single pause)
- The issue is in async code that is hard to pause without changing behavior (Heisenbug territory)
- You are debugging a deployment pipeline or build script where connecting DevTools is impractical

For production debugging, structured logging (JSON logs with fields you can query) is more useful than `console.log`. Libraries like Pino or Winston give you log levels, output formats, and queryable output.

The `--inspect` flag is the right default for complex bugs where you need to understand state at a specific point. It is faster than adding and removing console.log statements once you build the habit.
