---
title: "Observability: logs, metrics, traces and how they differ."
description: "The three pillars of observability -- logs, metrics, and distributed traces -- what each tells you, and how they work together."
pubDate: 2025-12-11
tags: ["DevOps", "Monitoring"]
draft: false
---

When something breaks in production, you need to answer three questions: what happened, how severe is it, and where in the system did it originate? Logs, metrics, and traces are three different tools for answering those questions, and they're most useful when you have all three.

## Logs: what happened

A log is a timestamped record of a discrete event. Something happened; you wrote it down.

```javascript
// Unstructured (hard to query)
console.log(`User ${userId} paid $${amount} for order ${orderId}`);

// Structured (queryable)
console.log(JSON.stringify({
  level: "info",
  event: "payment.completed",
  userId,
  orderId,
  amount,
  currency: "USD",
  timestamp: new Date().toISOString(),
  durationMs: 234
}));
```

Structured logs (JSON) can be indexed and queried by field. "Show me all failed payments over $1000 in the last hour" is a query, not a grep.

Log levels convey urgency:
- `debug`: Detailed information for development, usually disabled in production
- `info`: Normal operations, notable events
- `warn`: Something unexpected that didn't cause a failure
- `error`: Something failed, action may be required
- `fatal`: The system can't continue

Use a logging library that handles structured output and respects levels:

```javascript
import pino from "pino";

const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  formatters: {
    level: (label) => ({ level: label }) // use string level names
  }
});

logger.info({ userId, orderId, amount }, "Payment completed");
logger.error({ err, userId, orderId }, "Payment failed");
```

## Metrics: how the system is performing

A metric is a numerical measurement over time. Instead of "user 123 paid $50," a metric is "5 payments per second" or "p99 payment latency is 340ms."

Metrics are aggregated. You lose individual event details but gain the ability to see trends, set thresholds, and trigger alerts.

Key metric types:
- **Counter**: A monotonically increasing value. Requests served, errors thrown, messages processed.
- **Gauge**: A value that goes up and down. Active connections, memory usage, queue depth.
- **Histogram**: Distribution of values. Request durations, response sizes.

Using the Prometheus client for Node.js:

```javascript
import { Counter, Histogram, Registry } from "prom-client";

const registry = new Registry();

const httpRequestsTotal = new Counter({
  name: "http_requests_total",
  help: "Total HTTP requests",
  labelNames: ["method", "route", "status"],
  registers: [registry]
});

const httpRequestDuration = new Histogram({
  name: "http_request_duration_seconds",
  help: "HTTP request duration in seconds",
  labelNames: ["method", "route"],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [registry]
});

// In middleware
app.use((req, res, next) => {
  const end = httpRequestDuration.startTimer({ method: req.method, route: req.path });
  res.on("finish", () => {
    end();
    httpRequestsTotal.inc({ method: req.method, route: req.path, status: res.statusCode });
  });
  next();
});

// Prometheus scrape endpoint
app.get("/metrics", async (req, res) => {
  res.set("Content-Type", registry.contentType);
  res.end(await registry.metrics());
});
```

Common metrics to track for a web service:
- Request rate (requests/second)
- Error rate (5xx responses / total responses)
- Latency (p50, p95, p99)
- Saturation (CPU, memory, queue depth)

## Traces: where time was spent

A trace follows a single request through your system, recording the time spent in each operation. For a web request that queries a database and calls an external API, a trace shows exactly how long each step took.

```
Trace: POST /checkout (total: 523ms)
├── auth middleware (12ms)
├── validate cart (8ms)
├── charge payment (350ms)
│   ├── stripe API call (340ms)
│   └── record transaction in DB (10ms)
└── send confirmation email (153ms)
    ├── render template (3ms)
    └── sendgrid API call (150ms)
```

Without a trace, you know the request took 523ms. With a trace, you know the Stripe API call took 340ms and the SendGrid call took 150ms. You know where to optimize.

Using OpenTelemetry (the standard tracing library):

```javascript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { trace } from "@opentelemetry/api";

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
  })
});
sdk.start();

// Manual spans for important operations
const tracer = trace.getTracer("my-service");

async function chargePayment(amount, customerId) {
  const span = tracer.startSpan("charge.payment");
  span.setAttributes({ amount, customerId });

  try {
    const result = await stripe.charges.create({ amount, customer: customerId });
    span.setStatus({ code: SpanStatusCode.OK });
    return result;
  } catch (err) {
    span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
    span.recordException(err);
    throw err;
  } finally {
    span.end();
  }
}
```

HTTP instrumentation libraries can auto-instrument Express, fetch, and database clients, adding spans automatically.

## How they work together

The three pillars answer different questions:

- **Metric alert fires**: p99 latency increased 3x. Something is slow.
- **Traces**: Find the slowest requests. The database query in `GET /products` takes 800ms.
- **Logs**: Look at logs around slow requests. Find `slow query: full table scan on products`. Add an index.

You need all three. Metrics tell you there's a problem. Traces tell you where. Logs tell you why.

Popular observability platforms that provide all three: Datadog, Honeycomb, Grafana (with Prometheus + Loki + Tempo), Signoz (open source). For smaller applications, Logtail + Axiom for logs, Vercel Analytics or Sentry for performance are sufficient starting points.
