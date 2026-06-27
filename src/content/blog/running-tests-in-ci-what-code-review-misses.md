---
title: "Running tests in CI: the job that catches what code review misses."
description: "Why automated tests in CI catch bugs that code review doesn't, and how to structure a test job that provides real signal."
pubDate: 2025-06-05
tags: ["CI-CD", "Testing"]
draft: false
---

Code review is good at catching logic errors that are visible in the diff. It is bad at catching regressions in code that the PR does not touch. Tests in CI catch both. That asymmetry is why CI tests matter even on teams with rigorous review cultures.

## What code review catches, what it doesn't

A reviewer can spot a null check you forgot, an off-by-one error, or an API response you're not handling. A reviewer cannot easily see that the utility function you changed in `utils/date.ts` broke the invoice date calculation in `billing/invoice.ts` three files away.

Tests run the whole codebase against every change. CI is the only reviewer that checks all call sites of every function you modified.

## A practical CI test job

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - run: npm ci

      - name: Run migrations
        run: npm run db:migrate
        env:
          DATABASE_URL: postgres://postgres:testpassword@localhost:5432/testdb

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:testpassword@localhost:5432/testdb

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
```

The `services` block spins up a real PostgreSQL container that your tests can talk to. No mocking the database -- tests run against the same schema your migrations create.

## Separating unit and integration tests

Unit tests run fast (seconds) and have no external dependencies. Integration tests hit the database, file system, or external APIs and run slower.

Separate them so you can get fast feedback from unit tests while integration tests run in parallel:

```yaml
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm run test:unit

  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm run db:migrate
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/test
      - run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/test
```

Both jobs run in parallel. A unit test failure gives you signal in 30 seconds, before the integration tests finish.

## Test isolation in CI

Tests that pass locally and fail in CI usually have one of these problems:

**Order dependence**: Tests that rely on being run in a specific order, or on state left by a previous test. In CI, test runners may execute in different order or in parallel.

**Environment assumptions**: Tests that read from `~/.env` or assume a specific timezone. CI runners start clean with no local config.

**Timing assumptions**: Tests that use `setTimeout` with hardcoded durations. CI runners may be slower under load.

**Missing seed data**: Tests that assume database records exist without seeding them.

Fix these systematically:
```javascript
// Bad: assumes some other test created the user
it("updates user email", async () => {
  await updateEmail(1, "new@example.com");
});

// Good: creates its own test data
it("updates user email", async () => {
  const user = await createUser({ email: "old@example.com" });
  await updateEmail(user.id, "new@example.com");
  const updated = await getUser(user.id);
  expect(updated.email).toBe("new@example.com");
});
```

## Code coverage as a signal, not a target

Coverage reports tell you which lines of code were executed by tests. 80% coverage doesn't mean 80% of your bugs are caught; it means 80% of lines were touched at least once.

Coverage is useful for finding completely untested modules:

```json
// jest.config.js
{
  "collectCoverage": true,
  "coverageThreshold": {
    "global": {
      "branches": 70,
      "functions": 80,
      "lines": 80
    }
  }
}
```

Setting a threshold fails the CI job if coverage drops below the floor. This prevents the gradual erosion of test coverage as features are added without tests.

## Making test failures actionable

A CI failure is useful only if you can quickly diagnose it. Keep these principles:

- Test names describe the behavior under test: `"returns 404 when user not found"` not `"test1"`
- Each test asserts one thing
- Test output includes the actual vs expected values

A test suite that runs in 3 minutes, tests realistic scenarios, and produces readable failure messages is worth more than a suite with 90% coverage that takes 20 minutes and produces cryptic assertion errors.

