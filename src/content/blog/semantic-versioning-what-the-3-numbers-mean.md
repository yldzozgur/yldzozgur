---
title: "Semantic versioning: what the 3 numbers mean and when to bump each."
description: "A practical guide to semver -- MAJOR.MINOR.PATCH -- with real rules for when to increment each and how package managers use it."
pubDate: 2026-01-05
tags: ["Architecture"]
draft: false
---

Semantic versioning (semver) is a convention for version numbers that encodes meaning into the number itself. The format is `MAJOR.MINOR.PATCH` -- for example, `2.4.1`. Each number communicates something specific about what changed.

## The three numbers

**PATCH** increments when you make backwards-compatible bug fixes. Users can upgrade without risk of breakage.

```
2.4.1 -> 2.4.2  (fixed a null pointer exception in the parser)
```

**MINOR** increments when you add functionality in a backwards-compatible way. Existing code still works, but new features are available.

```
2.4.2 -> 2.5.0  (added an optional `timeout` parameter to fetch())
```

**MAJOR** increments when you make incompatible API changes. Users must change their code to upgrade.

```
2.5.0 -> 3.0.0  (removed the deprecated v1 authentication methods)
```

When you increment MAJOR, MINOR resets to 0. When you increment MINOR, PATCH resets to 0. So after `2.5.0 -> 3.0.0`, the next patch release is `3.0.1`, not `3.5.1`.

## Version 0.x.x is special

A MAJOR version of 0 signals that the public API is not yet stable. Breaking changes can happen in MINOR releases. This is common for libraries in early development:

```
0.1.0 -> 0.2.0  (may include breaking changes -- this is fine in v0)
0.9.0 -> 1.0.0  (now the API is stable and semver rules apply strictly)
```

This is why a dependency on `"^0.4.0"` is riskier than `"^1.4.0"`.

## How npm uses semver ranges

When you write a version in `package.json`, you're not specifying an exact version -- you're specifying a range. npm resolves that range to a specific version.

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "~4.17.21",
    "uuid": "9.0.0"
  }
}
```

The caret `^` means "compatible with this version" -- allow MINOR and PATCH updates but not MAJOR. `^4.18.0` matches any `4.x.y` where `x >= 18`.

The tilde `~` is more restrictive: allow PATCH updates only. `~4.17.21` matches `4.17.x` but not `4.18.0`.

No prefix means exactly this version.

You can verify what a range resolves to:

```bash
npm info express versions --json | node -e "
  const semver = require('semver');
  const v = JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'));
  console.log(semver.maxSatisfying(v, '^4.18.0'));
"
```

## What counts as a breaking change

This is where teams get into trouble. Some changes that are technically breaking but easy to miss:

- Removing a function, method, or property
- Changing a function signature (adding a required parameter, changing parameter types)
- Changing the shape of a return value
- Changing error types or messages that code might catch
- Tightening validation (rejecting inputs that previously worked)
- Changing behavior that code depends on, even if the API signature is the same

A common mistake: adding a required field to a config object. Callers that pass an existing config object without the new field are now broken. That's a MAJOR bump, not a MINOR one.

## Pre-release and build metadata

Semver supports pre-release identifiers and build metadata:

```
2.0.0-alpha.1
2.0.0-beta.3
2.0.0-rc.1
2.0.0+build.20260105
```

Pre-release versions have lower precedence than the release. `2.0.0-alpha.1 < 2.0.0`. npm won't install a pre-release version unless you explicitly ask for it:

```bash
npm install express@4.0.0-beta.1
```

## Practical rules for library authors

**Deprecate before removing.** Before a MAJOR bump, mark things deprecated in a MINOR release. Give users a migration path.

**Document breaking changes.** A CHANGELOG with a `BREAKING CHANGE` section tells users exactly what they need to update.

**Use conventional commits to automate versioning.** Tools like `semantic-release` parse commit messages to determine what version to publish:

```
feat: add optional timeout parameter    -> MINOR bump
fix: handle null response from parser   -> PATCH bump
feat!: remove v1 auth endpoints         -> MAJOR bump
```

```bash
# .releaserc
{
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/npm",
    "@semantic-release/github"
  ]
}
```

## Why it matters as a consumer

When you audit your `package.json`, semver ranges tell you your exposure. A dependency pinned to an exact version will never get bug fixes automatically. A dependency with `^` will get MINOR updates -- which are supposed to be safe, but library authors make mistakes.

`npm outdated` shows what's available versus what you have. Paired with `npm audit`, you can see which outdated packages have known vulnerabilities. Running these regularly is how you stay ahead of the problem rather than behind it.
