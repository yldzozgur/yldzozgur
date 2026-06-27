---
title: "Structured logs: why JSON beats printf in production."
description: "What structured logging is, why plain text logs break down at scale, and how to implement structured logging in common languages."
pubDate: 2025-07-14
tags: ["DevOps"]
draft: false
---

Logs are the primary debugging tool for production systems. When something breaks at 2am, the log is what you have. The format of those logs determines whether you spend 5 minutes or 45 minutes finding the problem.

## The problem with printf-style logs

Printf-style logging looks like this:

```
2025-07-14 03:42:11 INFO  User 4821 created order 9923 for $49.99
2025-07-14 03:42:11 ERROR Payment failed for order 9923: card declined
2025-07-14 03:42:12 INFO  User 4821 retried payment for order 9923
```

This is readable by a human staring at a terminal. It is not queryable by a log aggregation system. To find all failed payments in the last hour, you need a regex. To count how many users hit a specific error, you need awk. To correlate a request ID across multiple log lines, you need grep and manual inspection.

As soon as log volume exceeds what one person can read, printf logs become expensive to use.

## Structured logs

Structured logging emits each log entry as a machine-parseable record, typically JSON:

```json
{"timestamp":"2025-07-14T03:42:11Z","level":"info","event":"order_created","user_id":4821,"order_id":9923,"amount_cents":4999}
{"timestamp":"2025-07-14T03:42:11Z","level":"error","event":"payment_failed","order_id":9923,"reason":"card_declined","processor":"stripe"}
{"timestamp":"2025-07-14T03:42:12Z","level":"info","event":"payment_retry","user_id":4821,"order_id":9923}
```

Every field is a key-value pair. A log aggregation platform like Datadog, Loki, or CloudWatch Logs Insights can now run SQL-like queries:

```sql
SELECT order_id, COUNT(*) as failures
FROM logs
WHERE event = 'payment_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY order_id
ORDER BY failures DESC
```

This takes seconds. The same analysis on unstructured logs takes minutes of regex crafting.

## Implementation in common languages

**Node.js with pino:**

```javascript
import pino from 'pino';

const logger = pino({
  level: 'info',
  base: { service: 'payment-api', env: process.env.NODE_ENV },
});

logger.info({ user_id: 4821, order_id: 9923, amount_cents: 4999 }, 'order_created');
logger.error({ order_id: 9923, reason: 'card_declined' }, 'payment_failed');
```

Pino is the fastest Node.js JSON logger. The first argument is the structured fields object, the second is the human-readable message. Both end up in the JSON output.

**Python with structlog:**

```python
import structlog

log = structlog.get_logger()
log = log.bind(service="payment-api")

log.info("order_created", user_id=4821, order_id=9923, amount_cents=4999)
log.error("payment_failed", order_id=9923, reason="card_declined")
```

**Go with zap:**

```go
import "go.uber.org/zap"

logger, _ := zap.NewProduction()
defer logger.Sync()

logger.Info("order_created",
    zap.Int("user_id", 4821),
    zap.Int("order_id", 9923),
    zap.Int("amount_cents", 4999),
)
```

## Context propagation

The real power of structured logs comes from binding context fields that flow through the entire request lifecycle. A request ID generated at the entry point attaches to every log line produced during that request's execution:

```javascript
import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';

const requestContext = new AsyncLocalStorage();

// Middleware
app.use((req, res, next) => {
  const ctx = { request_id: randomUUID(), user_id: req.user?.id };
  requestContext.run(ctx, next);
});

// Logging wrapper
function log(level, event, fields = {}) {
  const ctx = requestContext.getStore() ?? {};
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    event,
    ...ctx,
    ...fields,
  }));
}
```

Now every log line from a single request shares the same `request_id`. In the log platform, filtering by `request_id = "abc-123"` shows the complete execution path for that one request, in chronological order, across all services that logged it.

## What to log

Log at event boundaries, not at every line of code. Useful events:

- Request received (with method, path, user identity)
- Request completed (with status code and duration)
- External calls made and their outcome (database queries over a threshold, outbound HTTP requests)
- Business events (order created, payment processed, user registered)
- Errors with full context (never just the exception message, always include the identifiers needed to reproduce)

Do not log sensitive data. Passwords, card numbers, tokens, and personally identifiable information do not belong in logs. If a third-party log aggregator is ingesting your logs, that data is now in their system.

## Log levels

Use levels consistently:

- `debug`: fine-grained developer information, off in production
- `info`: normal business events, on in production
- `warn`: unexpected but handled conditions
- `error`: failures that require attention

Setting the log level to `info` in production means debug logs are suppressed without changing code. Bumping to `debug` during an incident reveals detailed execution context.

Structured logs transform debugging from archaeology into querying.
