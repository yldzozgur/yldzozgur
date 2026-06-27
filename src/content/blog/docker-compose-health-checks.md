---
title: "Health checks in docker-compose: making containers wait for each other."
description: "How to use healthcheck and condition: service_healthy to ensure dependent containers only start after their dependencies are actually ready, not just running."
pubDate: 2024-10-28
tags: ["Docker"]
draft: false
---

`depends_on` in docker-compose does not do what most people expect. It ensures containers start in order, but it does not wait for a container to be ready before starting the next one. A database container that appears "running" may still be initializing. Your API container starts, tries to connect, fails, and crashes.

Health checks solve this. They let you define what "ready" actually means, and `condition: service_healthy` makes dependent services wait until that condition is met.

## The problem with depends_on alone

```yaml
# This does NOT guarantee the database is ready
services:
  api:
    build: ./api
    depends_on:
      - db

  db:
    image: postgres:16
```

With this configuration, `api` starts immediately after the `db` container process launches. PostgreSQL takes a few seconds to initialize its data directory and start accepting connections. The `api` crashes on its first connection attempt.

The common workaround is a retry loop in application code. That works, but it requires every service to implement its own retry logic. A cleaner solution is to declare health at the infrastructure level.

## Defining a health check

A health check is a command that Docker runs inside the container periodically. If the command exits 0, the container is healthy. If it exits non-zero, it is unhealthy. Docker tracks the status and surfaces it in `docker ps` and `docker inspect`.

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
```

The parameters:

- **`test`**: the command to run. `CMD-SHELL` passes the string to `/bin/sh -c`, so you can use shell syntax. `CMD` takes an exec array without shell processing.
- **`interval`**: how often to run the check after the previous one completes.
- **`timeout`**: how long to wait for the command to finish before treating it as failed.
- **`retries`**: how many consecutive failures before marking the container unhealthy.
- **`start_period`**: a grace period during startup where failures don't count toward the retry limit. Useful for slow-starting services.

## Using condition: service_healthy

Once a service has a health check, dependents can wait for it:

```yaml
services:
  api:
    build: ./api
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
```

Now `api` will not start until `db` reports healthy. Docker Compose polls the health status and delays the dependent service.

## Health checks for common services

**Redis:**
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 5
```

**MySQL:**
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$$MYSQL_ROOT_PASSWORD"]
  interval: 5s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**A Node.js API with a /health endpoint:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 15s
```

The `|| exit 1` is important when using `curl`. By default `curl` returns exit 0 even on HTTP errors. The `-f` flag makes it exit non-zero on HTTP 4xx/5xx, but adding the explicit `exit 1` makes the intent clear.

## Checking health status from the CLI

```bash
# See health status in container list
docker ps

# Detailed health info including recent check output
docker inspect --format='{{json .State.Health}}' container_name | jq

# Follow logs while waiting for healthy
docker-compose up --wait
```

The `--wait` flag (added in Compose v2) tells Compose to wait for all services with health checks to become healthy before returning. It exits non-zero if any service fails to become healthy within the configured timeout.

## Chaining multiple dependencies

A service can depend on multiple services with different conditions:

```yaml
services:
  worker:
    build: ./worker
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully

  migrations:
    build: ./migrations
    command: npm run migrate
    depends_on:
      db:
        condition: service_healthy
```

The `service_completed_successfully` condition waits for a container to exit with code 0. This is the right condition for one-shot containers like database migration runners: you want them to finish before the main application starts.

## What health checks do not replace

Health checks handle startup ordering. They do not handle runtime failures after startup. If your database crashes at 3am, the dependent service will not automatically restart or know to reconnect through health checks alone.

For runtime resilience, your application code still needs connection retry logic, circuit breakers, and graceful degradation. Health checks and application-level resilience are complementary, not interchangeable. Health checks solve the startup race condition specifically.
