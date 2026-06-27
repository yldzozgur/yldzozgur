---
title: "Health check endpoints: what belongs in them."
description: "What health check endpoints should verify, the difference between liveness and readiness, and how to implement them correctly."
pubDate: 2025-07-17
tags: ["DevOps"]
draft: false
---

Every service that runs in a container orchestration platform needs health check endpoints. Kubernetes, ECS, and load balancers call these endpoints to decide whether to send traffic to an instance. A bad health check causes unnecessary restarts or, worse, routes traffic to broken instances.

## The two types of health checks

Modern orchestration platforms distinguish between two probes with different semantics.

**Liveness** answers: is this process still alive and not stuck? A failing liveness probe causes the container to restart. Liveness should fail only for conditions where a restart would actually fix the problem - deadlocks, infinite loops, corrupted internal state.

**Readiness** answers: is this instance ready to serve traffic? A failing readiness probe removes the instance from load balancer rotation but does not restart it. Readiness should fail when the instance cannot currently handle requests - database connection unavailable, cache warming in progress, external dependency down.

```yaml
# Kubernetes pod spec
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 2
```

## What belongs in a liveness endpoint

The liveness endpoint should be lightweight and fast. It checks that the application process is functional, not that all dependencies are reachable.

```python
from flask import Flask, jsonify
import time

app = Flask(__name__)
START_TIME = time.time()

@app.route('/health/live')
def liveness():
    return jsonify({
        'status': 'ok',
        'uptime_seconds': int(time.time() - START_TIME)
    }), 200
```

A liveness endpoint that checks the database will cause container restarts during database outages. This is wrong. The database being down does not mean the application is broken in a way that a restart would fix. Restarting just adds churn and risks losing in-flight requests.

## What belongs in a readiness endpoint

Readiness verifies that the instance can actually serve requests right now. This means checking dependencies that are required for the application to function.

```python
import redis
import psycopg2
from flask import jsonify

db_pool = create_db_pool()
cache = redis.Redis()

@app.route('/health/ready')
def readiness():
    checks = {}
    status_code = 200

    # Database check
    try:
        conn = db_pool.getconn()
        conn.cursor().execute('SELECT 1')
        db_pool.putconn(conn)
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = str(e)
        status_code = 503

    # Cache check
    try:
        cache.ping()
        checks['cache'] = 'ok'
    except Exception as e:
        checks['cache'] = str(e)
        status_code = 503

    return jsonify({
        'status': 'ok' if status_code == 200 else 'degraded',
        'checks': checks
    }), status_code
```

Return 200 when ready, 503 when not. Return a JSON body with the status of each dependency so operators can see at a glance what is failing without needing to dig through logs.

## Startup probe

Some applications take time to initialize - loading ML models, warming caches, running database migrations. A startup probe gives the application time to become ready without triggering liveness failures during startup.

```yaml
startupProbe:
  httpGet:
    path: /health/live
  failureThreshold: 30
  periodSeconds: 10
```

This allows up to 5 minutes (30 * 10s) for the application to become live. Once it passes the startup probe, the regular liveness probe takes over with its shorter tolerances.

## Dependency timeout

Health check endpoints need aggressive timeouts on their dependency checks. If a database check hangs for 30 seconds, the health check endpoint itself hangs, and the orchestrator marks the instance as failed.

```python
import socket

def check_database_with_timeout(timeout=2):
    try:
        conn = psycopg2.connect(
            dsn=DATABASE_URL,
            connect_timeout=timeout
        )
        conn.cursor().execute('SELECT 1')
        conn.close()
        return True
    except Exception:
        return False
```

Two seconds is a reasonable timeout for a health check dependency verification. If the database does not respond in two seconds, something is wrong and the instance should stop receiving traffic.

## What not to put in health checks

Avoid calling external third-party APIs in health checks. If Stripe's API is slow, your health check will time out, your readiness probe will fail, and your service will take itself out of rotation. Your application is not broken. The health check is giving a false negative.

If your application uses a third-party service, track its connectivity as a separate metric and alert on it separately. Do not let a third-party outage cause your health checks to fail unless that dependency is truly required for every request.

## The /metrics endpoint pattern

Beyond health checks, a `/metrics` endpoint in Prometheus format gives orchestration and alerting systems quantitative data:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 12345
http_requests_total{method="POST",status="500"} 3
```

Health checks tell the orchestrator whether to send traffic. Metrics tell operators what is happening to that traffic. Both are necessary.

Well-designed health checks reduce on-call incidents by ensuring that broken instances do not receive traffic and that functional instances are not restarted unnecessarily.
