---
title: "path.join vs path.resolve: not interchangeable. The difference matters."
description: "path.join concatenates path segments. path.resolve builds an absolute path. Using the wrong one produces different results depending on environment."
pubDate: 2024-04-08
tags: ["Node.js"]
draft: false
---

`path.join` and `path.resolve` are both in Node's `path` module, they both handle path segments, and they both normalize the result. Many developers use them interchangeably, but they behave differently in ways that produce real bugs.

## path.join: concatenation with normalization

`path.join` concatenates path segments using the platform separator and normalizes the result:

```js
const path = require("path");

path.join("src", "utils", "helpers.js"); // "src/utils/helpers.js"
path.join("/home", "user", "docs"); // "/home/user/docs"
path.join("a", "..", "b"); // "b" — normalizes ..
path.join("a//b", "//c"); // "a/b/c" — normalizes double slashes
```

`path.join` is purely a string operation on the provided segments. It does not look at the file system or care about the current directory.

If you pass an absolute segment in the middle, `path.join` treats it as a string:

```js
path.join("/home", "/root", "file.txt"); // "/home/root/file.txt"
// Note: /root did NOT reset the path
```

## path.resolve: building absolute paths

`path.resolve` processes segments from right to left and stops when it has built an absolute path:

```js
path.resolve("file.txt"); // /current/working/directory/file.txt
path.resolve("src", "utils"); // /cwd/src/utils
path.resolve("/home/user", "docs"); // /home/user/docs
path.resolve("/home/user", "/root"); // /root — absolute segment resets the path
```

Key difference: if an absolute path appears in the arguments, `path.resolve` resets to that absolute path and continues from there:

```js
path.join("a", "/b", "c"); // "a/b/c" — /b treated as string
path.resolve("a", "/b", "c"); // "/b/c" — /b resets the base
```

When you call `path.resolve` with only relative paths, it prepends the current working directory to make the result absolute.

## When each one is correct

**Use `path.join` when:**
- Assembling parts of a relative path
- Combining a known base with relative segments where the base stays fixed
- You want to normalize path separators without anchoring to cwd

```js
// Correct: joining relative path segments
const configPath = path.join(__dirname, "..", "config", "app.json");
```

**Use `path.resolve` when:**
- You need an absolute path
- You are resolving user-provided paths that might be absolute or relative
- You want behavior similar to `cd` in a shell

```js
// Correct: resolving a user-provided path to absolute
function getAbsolutePath(input) {
  return path.resolve(input); // relative paths become absolute from cwd
}
```

## __dirname and __filename

`__dirname` is the absolute path of the directory containing the current module. It is the most reliable base for building file paths in Node.js:

```js
// Correct — works regardless of where the process was started
const templatePath = path.join(__dirname, "templates", "email.html");

// Incorrect — breaks if the process was started from a different directory
const templatePath = path.join("templates", "email.html");
```

When using ES modules (where `__dirname` is not available), reconstruct it:

```js
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const templatePath = join(__dirname, "templates", "email.html");
```

## Path traversal security

When handling user-provided file paths, validate that the resolved path stays within the intended directory:

```js
const path = require("path");
const fs = require("fs");

function serveFile(userInput, baseDir) {
  const resolved = path.resolve(baseDir, userInput);

  // Check that the resolved path is still inside baseDir
  if (!resolved.startsWith(path.resolve(baseDir) + path.sep)) {
    throw new Error("Access denied: path traversal attempt");
  }

  return fs.readFileSync(resolved, "utf8");
}
```

Without this check, a user passing `../../etc/passwd` could read files outside the intended directory.

## path.normalize

If you just need to clean up a path without joining or resolving:

```js
path.normalize("/home//user/../docs/./file.txt");
// "/home/docs/file.txt"
```

## Platform differences

`path.join` and `path.resolve` use the platform's separator automatically. On Windows, the separator is `\`. On Unix it is `/`. Using `path.join` instead of string concatenation ensures your code works on both platforms.

```js
// Correct
path.join("src", "utils", "helpers.js"); // "src/utils/helpers.js" on Unix, "src\utils\helpers.js" on Windows

// Fragile
"src" + "/" + "utils" + "/" + "helpers.js"; // broken on Windows
```

The short version: use `path.join` for assembling relative paths with `__dirname` as the base, and `path.resolve` when you need an absolute path or are handling input that might be absolute.
