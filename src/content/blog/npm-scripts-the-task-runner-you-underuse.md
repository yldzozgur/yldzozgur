---
title: "npm scripts: the task runner you already have but probably underuse."
description: "How npm scripts work, the lifecycle hooks available, and patterns that replace external task runners for most projects."
pubDate: 2026-01-08
tags: ["Architecture"]
draft: false
---

Before you reach for Gulp, Grunt, or a custom Makefile, consider what's already in your `package.json`. npm scripts can handle most build automation tasks, they run in a shell with your local `node_modules/.bin` on the PATH, and every Node.js developer already knows how to run them.

## The basics

Scripts live in the `scripts` field of `package.json`:

```json
{
  "scripts": {
    "start": "node server.js",
    "build": "tsc",
    "test": "jest",
    "lint": "eslint src/"
  }
}
```

Run them with `npm run <name>`. The special scripts `start`, `test`, `stop`, and `restart` can be run without the `run` keyword: `npm start`, `npm test`.

## The PATH trick

When npm runs a script, it prepends `./node_modules/.bin` to PATH. This means you can call locally installed CLI tools directly without `npx` or a full path:

```json
{
  "scripts": {
    "build": "tsc && rollup -c",
    "lint": "eslint . && prettier --check ."
  }
}
```

Both `tsc`, `rollup`, `eslint`, and `prettier` here refer to the locally installed versions. No global installs required, and everyone on the team uses the same version.

## Lifecycle hooks

npm has a set of built-in lifecycle hooks that run automatically before or after named scripts. Prefix `pre` or `post` to any script name:

```json
{
  "scripts": {
    "prebuild": "rm -rf dist/",
    "build": "tsc",
    "postbuild": "echo Build complete"
  }
}
```

Running `npm run build` automatically executes `prebuild`, then `build`, then `postbuild`. This is cleaner than chaining everything into one long command.

There are also built-in lifecycle hooks that run around install:

- `prepare` -- runs before `npm publish` and after `npm install`
- `prepublishOnly` -- runs only before `npm publish`, not on install
- `preinstall`, `postinstall` -- before/after the package tree is installed

```json
{
  "scripts": {
    "prepare": "husky install",
    "prepublishOnly": "npm run build && npm test"
  }
}
```

## Chaining and parallelism

Run scripts sequentially with `&&` (stop on failure) or `;` (continue regardless):

```json
{
  "scripts": {
    "check": "npm run lint && npm run test && npm run build"
  }
}
```

Run scripts in parallel with `&` (Unix) or use `concurrently` for cross-platform support:

```json
{
  "devDependencies": {
    "concurrently": "^8.0.0"
  },
  "scripts": {
    "dev": "concurrently \"npm run dev:server\" \"npm run dev:client\"",
    "dev:server": "nodemon src/server.ts",
    "dev:client": "vite"
  }
}
```

## Passing arguments

Arguments after `--` are forwarded to the script:

```bash
npm run test -- --watch
npm run build -- --sourcemap
```

Inside the script, these arrive as additional CLI arguments to whatever tool is running.

You can also use environment variables to parameterize scripts:

```json
{
  "scripts": {
    "build:prod": "NODE_ENV=production vite build",
    "build:staging": "NODE_ENV=staging vite build"
  }
}
```

On Windows, `cross-env` handles this portably:

```json
{
  "scripts": {
    "build": "cross-env NODE_ENV=production vite build"
  }
}
```

## Organizing complex builds

For projects with many steps, break scripts into small named pieces and compose them:

```json
{
  "scripts": {
    "clean": "rm -rf dist/",
    "compile": "tsc --noEmit",
    "bundle": "vite build",
    "test": "vitest run",
    "lint": "eslint src/ --max-warnings 0",
    "typecheck": "tsc --noEmit",
    "ci": "npm run lint && npm run typecheck && npm run test && npm run bundle",
    "build": "npm run clean && npm run bundle"
  }
}
```

This is readable, each step is independently runnable for debugging, and CI just calls `npm run ci`.

## When to reach for something else

npm scripts are the right default. Consider a proper task runner when:

- You need file watching with incremental rebuilds across many interconnected tasks (Turborepo or Nx handle this with caching)
- You're in a monorepo where tasks have dependencies between packages
- Your build graph is complex enough that a dependency-aware runner saves meaningful time

For a single-package project, `package.json` scripts and `concurrently` handle most of what Gulp used to do, with less configuration and one fewer abstraction to maintain.
