---
title: "child_process: running shell commands from Node without shooting yourself."
description: "Node's child_process module lets you run shell commands, but the API choices matter. Here's how to use it safely and correctly."
pubDate: 2024-04-04
tags: ["Node.js"]
draft: false
---

Node.js can spawn child processes to run shell commands, other programs, or other Node scripts. The `child_process` module provides several functions, each suited for different situations. Using the wrong one can lead to security vulnerabilities or subtle bugs.

## The four main functions

- `exec`: run a shell command, buffer output
- `execFile`: run a file directly, buffer output
- `spawn`: stream output in real time
- `fork`: spawn a Node.js process with IPC

## exec: buffered shell command

```js
const { exec } = require("child_process");

exec("ls -la", (err, stdout, stderr) => {
  if (err) {
    console.error("Error:", err.message);
    return;
  }
  if (stderr) {
    console.error("Stderr:", stderr);
  }
  console.log(stdout);
});
```

`exec` runs the command in a shell (`/bin/sh` on Unix, `cmd.exe` on Windows). Output is buffered — you get it all at once when the process finishes.

The problem with `exec` and user input: shell injection. Never do this:

```js
// DANGEROUS — command injection vulnerability
const userInput = req.query.filename;
exec(`cat ${userInput}`, callback);
// User can pass: "file.txt && rm -rf /"
```

## execFile: safer alternative

```js
const { execFile } = require("child_process");

execFile("cat", ["file.txt"], (err, stdout, stderr) => {
  console.log(stdout);
});
```

`execFile` does not invoke a shell. Arguments are passed as an array and are not interpreted by a shell. There is no injection risk from arguments.

```js
// Safe with user input — arguments are not shell-interpolated
execFile("cat", [userInput], (err, stdout) => {
  console.log(stdout);
});
```

Use `execFile` (or `spawn`) whenever you are incorporating user-controlled values into a command.

## spawn: streaming output

For long-running commands or large output, `spawn` streams stdout and stderr:

```js
const { spawn } = require("child_process");

const child = spawn("grep", ["-r", "pattern", "./src"]);

child.stdout.on("data", (data) => {
  process.stdout.write(data);
});

child.stderr.on("data", (data) => {
  process.stderr.write(data);
});

child.on("close", (code) => {
  console.log(`Process exited with code ${code}`);
});
```

`spawn` returns a `ChildProcess` object with `stdout`, `stderr`, and `stdin` streams. Use it when output could be large or when you need to process output as it arrives.

## promisified versions

The `util.promisify` approach works for `exec` and `execFile`:

```js
const { promisify } = require("util");
const { exec, execFile } = require("child_process");

const execAsync = promisify(exec);
const execFileAsync = promisify(execFile);

async function runCommand() {
  try {
    const { stdout, stderr } = await execAsync("git log --oneline -10");
    return stdout.split("\n").filter(Boolean);
  } catch (err) {
    throw new Error(`Command failed: ${err.message}`);
  }
}
```

Node 12+ also has `child_process/promises`:

```js
const { exec } = require("child_process/promises");

const { stdout } = await exec("git status");
```

## Handling errors correctly

```js
const { execFile } = require("child_process/promises");

async function runGit(args) {
  try {
    const { stdout } = await execFile("git", args);
    return stdout.trim();
  } catch (err) {
    // err.code is the exit code
    // err.stdout and err.stderr contain the output
    if (err.code === 128) {
      throw new Error("Not a git repository");
    }
    throw new Error(`git ${args.join(" ")} failed: ${err.stderr}`);
  }
}

const branch = await runGit(["rev-parse", "--abbrev-ref", "HEAD"]);
```

Non-zero exit codes throw an error with `exec` and `execFile`. The error object has `code`, `stdout`, and `stderr` properties.

## fork: Node-to-Node communication

`fork` is for spawning another Node.js script with a built-in IPC channel:

```js
// parent.js
const { fork } = require("child_process");
const child = fork("./worker.js");

child.send({ task: "compute", data: largeDataset });

child.on("message", (result) => {
  console.log("Worker result:", result);
  child.kill();
});

// worker.js
process.on("message", ({ task, data }) => {
  const result = heavyComputation(data);
  process.send({ result });
});
```

`fork` is the simplest way to offload CPU-intensive work to a separate process without blocking the event loop.

## Shell option on spawn

If you need shell features (pipes, redirects, glob expansion) with spawn:

```js
spawn("cat file.txt | grep pattern", {
  shell: true, // enables shell interpretation
  stdio: "inherit", // inherit parent's stdio
});
```

`shell: true` reintroduces the injection risk. Only use it when you control the entire command string.

The rule: use `execFile` or `spawn` with array arguments when any part of the command comes from user input. Use `exec` only when the command is entirely under your control.
