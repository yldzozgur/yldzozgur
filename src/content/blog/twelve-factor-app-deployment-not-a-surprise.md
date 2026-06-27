---
title: "The 12-factor app: principles that make deployment not a surprise."
description: "A practical walkthrough of the 12-factor app methodology and how each factor prevents the common failure modes of deployment."
pubDate: 2025-11-13
tags: ["DevOps", "Architecture"]
draft: false
---

The 12-factor app methodology, developed at Heroku, is a set of practices for building software-as-a-service applications that are portable, scalable, and maintainable. Each factor addresses a specific category of operational pain.

## I. Codebase: one codebase, many deploys

One repository, multiple environments (staging, production). Not one repo per environment, not multiple apps from different codebases with shared libraries copy-pasted between them.

Feature flags handle environment-specific behavior within the single codebase. Environment variables handle configuration differences.

## II. Dependencies: explicitly declare, isolate

Don't rely on system-installed packages. Every dependency must be declared in a manifest (`package.json`, `requirements.txt`, `go.mod`) and installed in isolation.

Node.js with `package.json` and `node_modules` satisfies this. The exact dependency versions are locked in `package-lock.json`. Anyone who clones the repo and runs `npm ci` gets exactly the same dependency tree.

Vendoring (committing `node_modules`) is a valid approach for air-gapped environments but creates a huge repo. For most applications, a lockfile plus a private npm registry is sufficient.

## III. Config: store config in the environment

Anything that differs between deploys (database URLs, API keys, hostnames) must live in environment variables, not in the codebase.

```javascript
// Bad: config in code
const db = new Pool({ host: "prod-db.example.com", password: "secret" });

// Good: config in environment
const db = new Pool({ connectionString: process.env.DATABASE_URL });
```

The test: can you open-source the codebase without exposing credentials? If yes, your config is properly separated.

## IV. Backing services: treat as attached resources

Database, cache, queue, email provider -- these are attached resources. Swap a local PostgreSQL for a managed RDS by changing one environment variable. The code doesn't change.

```
DATABASE_URL=postgres://localhost/myapp   # local
DATABASE_URL=postgres://user:pass@rds-host/myapp  # production
```

This principle is what enables easy environment promotion and disaster recovery.

## V. Build, release, run: strict separation

Three distinct stages:

- **Build**: Compile code, bundle assets, install dependencies. No environment-specific values.
- **Release**: Combine the build artifact with environment config. Creates a versioned release.
- **Run**: Execute the release in the target environment.

No changes to code at runtime. If a release has a bug, you roll back to a previous release -- you don't patch the running process.

CI/CD pipelines enforce this. The artifact that passes CI tests is exactly what gets deployed to production.

## VI. Processes: execute as stateless processes

Application processes are stateless. They don't store persistent data locally. User sessions, uploaded files, cached data -- all go to external backing services (database, Redis, S3).

This makes horizontal scaling trivial. Add another process instance; it has the same capabilities as the others because all state is external. Remove a process; no data is lost.

## VII. Port binding: export services via port binding

The application is self-contained and binds to a port. There's no dependency on a runtime-injected webserver. Node.js with Express handles this naturally:

```javascript
const app = express();
app.listen(process.env.PORT ?? 3000);
```

The platform (Heroku, Kubernetes, Vercel) provides the port via `PORT` environment variable.

## VIII. Concurrency: scale out via the process model

Scale by running more processes, not by making one process bigger. Web processes handle HTTP. Worker processes handle background jobs. Each type can be scaled independently.

```
web: node server.js
worker: node worker.js
```

Horizontal scaling (more instances) is preferred over vertical scaling (larger instance). A single-threaded Node.js process handles concurrency well through the event loop; true parallelism comes from multiple processes.

## IX. Disposability: fast startup, graceful shutdown

Processes should start in seconds and shut down cleanly when they receive a SIGTERM:

```javascript
process.on("SIGTERM", async () => {
  console.log("SIGTERM received, shutting down...");
  server.close(async () => {
    await db.pool.end(); // Close DB connections
    process.exit(0);
  });
});
```

Fast startup enables rapid scaling. Graceful shutdown ensures in-flight requests complete before the process dies, and background jobs don't get cut off.

## X. Dev/prod parity: keep environments as similar as possible

Local development should mirror production. If production runs PostgreSQL 16, don't use SQLite locally. If production runs on Linux, develop on Linux (or in a container).

Docker Compose makes this achievable:

```yaml
services:
  db:
    image: postgres:16
  app:
    build: .
    environment:
      DATABASE_URL: postgres://postgres:postgres@db/myapp
```

The more dev/prod parity you have, the fewer "works on my machine" bugs reach production.

## XI. Logs: treat as event streams

Applications should write logs to stdout, not to files. The platform collects, routes, and aggregates them.

```javascript
// Good: write to stdout
console.log(JSON.stringify({ level: "info", message: "Request processed", duration: 45 }));

// Bad: write to files
fs.appendFileSync("/var/log/app.log", message);
```

Structured JSON logs are machine-parseable. Ship them to a log aggregation service (Datadog, Logtail, CloudWatch) for querying and alerting.

## XII. Admin processes: run as one-off processes

Database migrations, data backups, console sessions -- run as one-off processes using the same codebase and environment:

```bash
node scripts/migrate.js     # runs migrations
node scripts/seed.js        # seeds data
```

Never run admin tasks on a live production process by exec-ing into a container. Run them as ephemeral processes with the same configuration.

These twelve factors aren't a checklist to complete once. They're principles that guide architecture decisions. Following them consistently produces applications that are easier to operate, scale, and debug.
