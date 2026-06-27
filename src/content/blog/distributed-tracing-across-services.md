---
title: "Distributed tracing: following a request across multiple services."
description: "How distributed tracing tracks a request through multiple services using trace context propagation, and how to implement it with OpenTelemetry."
pubDate: 2025-12-15
tags: ["DevOps", "Monitoring"]
draft: false
---

When a request fails in a microservices system, which service is responsible? A user's checkout request might go through an API gateway, an auth service, an inventory service, and a payment service before completing. Without distributed tracing, debugging a cross-service failure is guesswork.

## The problem

In a monolith, a stack trace tells you exactly what happened. In a distributed system, each service has its own logs and there's no automatic connection between them. When the payment service returns an error, was it because the inventory service returned wrong data? Or did the auth service pass a bad token? You'd have to manually correlate logs across services by timestamp, which is slow and unreliable.

Distributed tracing solves this by propagating a shared identifier (trace ID) through every service call. All spans for a single user request share the same trace ID, so you can see the entire cross-service request path in one view.

## How trace context propagation works

When Service A calls Service B, it passes the trace context in HTTP headers:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

The W3C `traceparent` header format:
- `00`: version
- `4bf92f3577b34da6a3ce929d0e0e4736`: trace ID (same for all services in this request)
- `00f067aa0ba902b7`: parent span ID (Service A's span)
- `01`: flags (sampling decision)

Service B reads this header, creates its own span as a child of Service A's span, and passes the same trace ID forward if it calls Service C.

## Implementation with OpenTelemetry

OpenTelemetry is the standard, vendor-neutral tracing library. It handles context propagation automatically for HTTP clients and servers.

**Setting up in Node.js (must run before importing other modules):**

```javascript
// tracing.js - import this first!
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";

const sdk = new NodeSDK({
  serviceName: process.env.OTEL_SERVICE_NAME ?? "payment-service",
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? "http://localhost:4318/v1/traces"
  }),
  instrumentations: [getNodeAutoInstrumentations()]
});

sdk.start();
```

`getNodeAutoInstrumentations` auto-instruments:
- HTTP/HTTPS (incoming requests become spans, outgoing calls propagate context)
- Express, Fastify, Koa
- pg, mysql2, redis
- fetch, axios, undici

With auto-instrumentation, inter-service HTTP calls automatically propagate the `traceparent` header. You don't write the propagation code; the library handles it.

## Adding custom spans

Auto-instrumentation covers the edges (HTTP, DB). Add manual spans for important business logic:

```javascript
import { trace, SpanStatusCode } from "@opentelemetry/api";

const tracer = trace.getTracer("payment-service");

async function processPayment(orderId, amount, customerId) {
  const span = tracer.startSpan("payment.process", {
    attributes: {
      "order.id": orderId,
      "payment.amount": amount,
      "customer.id": customerId
    }
  });

  try {
    // Validate
    const validation = await tracer.startActiveSpan("payment.validate", async (vs) => {
      const result = await validateOrder(orderId);
      vs.end();
      return result;
    });

    if (!validation.valid) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: "Validation failed" });
      return { success: false, error: validation.reason };
    }

    // Charge
    const charge = await tracer.startActiveSpan("payment.charge_stripe", async (cs) => {
      const result = await stripe.charges.create({ amount, customer: customerId });
      cs.setAttributes({ "stripe.charge_id": result.id });
      cs.end();
      return result;
    });

    span.setAttributes({ "stripe.charge_id": charge.id });
    span.setStatus({ code: SpanStatusCode.OK });
    return { success: true, chargeId: charge.id };

  } catch (error) {
    span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}
```

## Sampling

Tracing every request at high traffic generates enormous amounts of data. Sampling sends only a fraction of traces to your backend.

**Head-based sampling**: Decision made at the start of the trace. Fast, but you might not sample the rare slow or errored request.

**Tail-based sampling**: Decision made after the trace is complete. You can always sample error traces and slow traces, regardless of your base rate.

```javascript
import { ParentBasedSampler, TraceIdRatioBased } from "@opentelemetry/sdk-trace-base";

const sampler = new ParentBasedSampler({
  root: new TraceIdRatioBased(0.1) // Sample 10% of new traces
  // But respect parent's sampling decision for child spans
});
```

Honeycomb and Grafana Tempo support tail-based sampling at the collector level, which lets you keep 100% of error/slow traces and sample the rest.

## Correlating logs with traces

Add the trace ID to your log entries so you can jump from logs to the corresponding trace:

```javascript
import { context, trace } from "@opentelemetry/api";
import pino from "pino";

const logger = pino({
  mixin() {
    const span = trace.getActiveSpan();
    if (!span) return {};
    const { traceId, spanId } = span.spanContext();
    return { traceId, spanId };
  }
});
```

Now every log line includes `traceId` and `spanId`. When you see an error in your log aggregator, you can click the trace ID to open the full trace in your tracing tool.

## Choosing a tracing backend

- **Jaeger**: Open source, self-hosted, part of the CNCF
- **Zipkin**: Open source, battle-tested
- **Grafana Tempo**: Open source, designed for high-volume tracing, pairs with Grafana
- **Honeycomb**: Managed, strong tooling for trace analysis
- **Datadog APM**: If you're already on Datadog

All of these accept OpenTelemetry data. If you instrument with OpenTelemetry, switching backends is a configuration change, not a code change.
