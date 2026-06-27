---
title: "Monorepo basics: when one repo actually makes sense."
description: "What monorepos solve, the tooling that makes them workable, and the tradeoffs you accept when you put everything in one place."
pubDate: 2026-01-15
tags: ["Architecture"]
draft: false
---

A monorepo is a single version control repository that contains multiple projects. This sounds simple, and the idea itself is -- but the tradeoffs and tooling around it are worth understanding before you move your whole organization into one.

## What problem it solves

Separate repos for separate packages create friction when those packages have dependencies on each other. Consider a company with a shared UI component library, a backend API, a web app, and a mobile app. With separate repos:

- Updating a component means publishing the library, bumping the version in each app, and opening separate PRs
- Refactoring a shared type means coordinating changes across multiple repos
- Local development of the app while iterating on the library requires `npm link` gymnastics

With a monorepo, you change the component and the apps using it in a single commit. The change is atomic. Code review sees the full scope of the change. The CI run tests everything that was affected.

## The basic structure

A typical monorepo with npm workspaces:

```
my-repo/
  package.json          (root -- declares workspaces)
  packages/
    ui/
      package.json      (name: "@company/ui")
    api/
      package.json      (name: "@company/api")
    web/
      package.json      (name: "@company/web", depends on @company/ui)
```

Root `package.json`:

```json
{
  "name": "my-repo",
  "private": true,
  "workspaces": ["packages/*"]
}
```

`npm install` at the root installs all packages and creates symlinks in `node_modules` for workspace packages. `@company/ui` in `web/node_modules` points to `packages/ui`. No publishing required for local development.

## Turborepo: the piece that makes it practical

npm workspaces handle installation. They don't handle build orchestration. If `web` depends on `ui`, you need to build `ui` before `web`. If you have 20 packages, you need a dependency graph.

Turborepo solves this with a task pipeline:

```json
// turbo.json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"]
    },
    "lint": {}
  }
}
```

`^build` means "run build in all packages this package depends on first." Turborepo builds the graph, runs tasks in the right order, and caches outputs so unchanged packages are never rebuilt:

```bash
turbo run build
# First run: builds everything
# Second run (no changes): cache hit, completes in <1s
```

The cache key is the hash of all input files for that package. Change a file in `ui`, and only `ui` and anything that depends on it gets rebuilt.

## What you give up

**Repo size.** A monorepo accumulates everything. Git history, branches, and pull requests all live in one place. With enough packages and history, `git clone` gets slow and GitHub PR lists get crowded.

**Access control.** GitHub doesn't support fine-grained permissions within a single repo (CODEOWNERS can restrict who can *merge*, but not who can *see* code). If different teams need different access levels, multiple repos may be necessary.

**CI complexity.** You need to detect which packages changed and only run CI for those. Without this, every push runs every test, which gets slow fast. Turborepo's `--filter` helps:

```bash
# Only run tests for packages affected by changes since main
turbo run test --filter=...[origin/main]
```

**Cognitive overhead.** A single large repo takes more effort to navigate, especially for new team members who don't know which packages do what.

## When it's the right choice

Monorepos work well when:

- Teams are small and share most of the codebase
- Packages have frequent cross-cutting changes
- You want atomic commits across multiple packages
- Dependency management overhead across repos is a real problem you're feeling

They work less well when:

- Teams are large and mostly independent
- You need access isolation between projects
- Packages are published independently to npm and rarely change together

The sweet spot is 2-10 closely related packages owned by one or two teams. Netflix and Google run large monorepos successfully, but they have dedicated tooling teams. For most companies, the right answer is somewhere between "one repo for everything" and "one repo per microservice."
