---
title: "GitHub Actions: the workflow file that runs your tests on every push."
description: "How to write a GitHub Actions workflow that runs your test suite on every push and pull request."
pubDate: 2025-06-02
tags: ["CI/CD", "GitHub"]
draft: false
---

GitHub Actions turns your repository into a CI system with no external services required. A YAML file in `.github/workflows/` is all it takes to run tests on every push.

## The anatomy of a workflow file

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test
```

That is a complete, working CI pipeline. Every push to `main` or `develop`, and every pull request targeting `main`, will trigger this job.

## Key concepts

**Triggers (`on`)**: Define when the workflow runs. `push` fires on direct pushes; `pull_request` fires when a PR is opened, updated, or synchronized. You can filter by branch, tag, or file path.

**Jobs**: Independent units of work that run on separate virtual machines. Jobs run in parallel by default unless you add a `needs` dependency.

**Steps**: Sequential commands within a job. Each step either runs a shell command (`run`) or uses a pre-built action (`uses`).

**Runners**: The VM that executes the job. `ubuntu-latest` is the most common. GitHub also provides `windows-latest` and `macos-latest`.

## Using `npm ci` instead of `npm install`

`npm ci` is the right command for CI environments:
- Installs exactly what's in `package-lock.json`
- Fails if `package-lock.json` doesn't exist or is out of sync with `package.json`
- Does not update the lockfile
- Faster on clean installs because it skips the resolution step

The `cache: "npm"` option in `setup-node` caches the npm cache directory between runs, so dependency installation only downloads changed packages.

## Caching dependencies manually

If you need more control over caching:

```yaml
- name: Cache node modules
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

The cache key includes a hash of `package-lock.json`. When lockfile changes, the cache misses and dependencies are reinstalled fresh. The `restore-keys` fallback lets it use a stale cache and only update changed packages.

## Running with environment variables

Tests that need database connections or API keys use environment variables:

```yaml
- name: Run tests
  run: npm test
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    NODE_ENV: test
```

Secrets are set in your repository's Settings > Secrets and variables > Actions. Never hardcode credentials in workflow files.

## Matrix builds: testing across versions

Test against multiple Node versions with a matrix:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ["18", "20", "22"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: "npm"
      - run: npm ci
      - run: npm test
```

This creates three parallel jobs, one per Node version. All three must pass for the workflow to succeed.

## Failing fast vs running all jobs

By default, if one matrix job fails, the others continue running. Add `fail-fast: true` to cancel the remaining jobs as soon as one fails, saving runner minutes:

```yaml
strategy:
  fail-fast: true
  matrix:
    node-version: ["18", "20", "22"]
```

For most projects, failing fast is the right default. For release verification where you want to know exactly which versions fail, set it to `false`.

## Branch protection rules

The CI workflow is only useful if you enforce it. In your repository Settings > Branches, add a branch protection rule for `main`:

- Require status checks to pass before merging
- Select your workflow job as a required check
- Enable "Require branches to be up to date before merging"

With this configured, a pull request cannot be merged until the test workflow passes. This is the hard enforcement that makes CI meaningful rather than advisory.

## Viewing results

Workflow runs appear in the Actions tab of your repository. Each run shows the trigger event, the jobs, and the output of each step. Failed steps show the exact error output. Workflow run logs are retained for 90 days by default.

For pull requests, the workflow status appears directly in the PR, with a link to the full logs when something fails. This is the feedback loop that makes CI useful day to day.
