---
title: "Circuit breakers: stopping a cascade failure before it takes everything down."
description: "How the circuit breaker pattern prevents cascade failures in distributed systems, with a Node.js implementation."
pubDate: 2025-12-18
tags: ["Architecture", "Node.js"]
draft: false
---

When an external service starts failing, your service starts failing too. If you keep calling the failing service, you're wasting resources on calls that will fail, the failing service never gets breathing room to recover, and the cascading failures spread. A circuit breaker stops you from hammering a service that's already down.

## The pattern

A circuit breaker wraps calls to an external service and tracks failures. It has three states:

**Closed** (normal): Calls pass through. Failures are tracked. When failures exceed a threshold, the circuit opens.

**Open** (failing fast): All calls fail immediately without hitting the external service. After a timeout, the circuit moves to half-open.

**Half-open** (testing recovery): A limited number of calls are allowed through. If they succeed, the circuit closes. If they fail, it opens again.

```
Closed → (failure threshold) → Open → (timeout) → Half-Open
                                                         ↓
                                              success → Closed
                                              failure → Open
```

## Why this helps

Without a circuit breaker, if your payment provider is down:
- Every user request that triggers a payment call waits for a timeout (e.g., 30 seconds)
- Your server has hundreds of threads/connections waiting on a dead service
- Your server becomes unresponsive to all requests, not just payment ones
- The overloaded payment provider never recovers because it keeps getting hammered

With a circuit breaker:
- After 5 failures, the circuit opens
- Subsequent payment calls fail immediately (no waiting)
- Your server stays responsive for non-payment requests
- The payment provider gets 60 seconds without load, has a chance to recover
- Half-open test calls confirm recovery before full traffic resumes

## A Node.js implementation

```javascript
const CircuitState = {
  CLOSED: "CLOSED",
  OPEN: "OPEN",
  HALF_OPEN: "HALF_OPEN"
};

class CircuitBreaker {
  constructor(fn, options = {}) {
    this.fn = fn;
    this.failureThreshold = options.failureThreshold ?? 5;
    this.successThreshold = options.successThreshold ?? 2;
    this.timeout = options.timeout ?? 60000; // ms before trying half-open
    this.halfOpenMaxCalls = options.halfOpenMaxCalls ?? 3;

    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.nextAttempt = Date.now();
    this.halfOpenCalls = 0;
  }

  async call(...args) {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() < this.nextAttempt) {
        throw new Error(`Circuit breaker OPEN. Retry after ${new Date(this.nextAttempt).toISOString()}`);
      }
      this.state = CircuitState.HALF_OPEN;
      this.halfOpenCalls = 0;
    }

    if (this.state === CircuitState.HALF_OPEN) {
      if (this.halfOpenCalls >= this.halfOpenMaxCalls) {
        throw new Error("Circuit breaker HALF_OPEN: max test calls reached");
      }
      this.halfOpenCalls++;
    }

    try {
      const result = await this.fn(...args);
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.successCount = 0;
        console.log("Circuit breaker: CLOSED (recovered)");
      }
    }
  }

  onFailure() {
    this.failureCount++;
    if (this.state === CircuitState.HALF_OPEN) {
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
      console.log("Circuit breaker: OPEN (half-open test failed)");
      return;
    }
    if (this.failureCount >= this.failureThreshold) {
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
      console.log(`Circuit breaker: OPEN (${this.failureCount} failures)`);
    }
  }

  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      nextAttempt: this.state === CircuitState.OPEN ? this.nextAttempt : null
    };
  }
}
```

Usage:

```javascript
// Wrap the external service call
const paymentBreaker = new CircuitBreaker(
  async (amount, customerId) => {
    const response = await fetch("https://payment-api.example.com/charge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, customerId }),
      signal: AbortSignal.timeout(5000) // 5s timeout per request
    });
    if (!response.ok) throw new Error(`Payment API error: ${response.status}`);
    return response.json();
  },
  { failureThreshold: 5, timeout: 60000 }
);

// In your handler
async function chargeCustomer(amount, customerId) {
  try {
    return await paymentBreaker.call(amount, customerId);
  } catch (error) {
    if (error.message.includes("Circuit breaker OPEN")) {
      // Return a friendly error without waiting on the failed service
      throw new ServiceUnavailableError("Payment service temporarily unavailable");
    }
    throw error;
  }
}
```

## Using existing libraries

`opossum` is a well-maintained circuit breaker library for Node.js:

```javascript
import CircuitBreaker from "opossum";

const breaker = new CircuitBreaker(callPaymentAPI, {
  timeout: 5000,          // Call times out after 5s
  errorThresholdPercentage: 50,  // Open when 50% of calls fail
  resetTimeout: 60000,    // Try again after 60s
  volumeThreshold: 10     // Minimum calls before evaluating
});

breaker.on("open", () => console.log("Circuit opened"));
breaker.on("halfOpen", () => console.log("Testing recovery"));
breaker.on("close", () => console.log("Circuit closed, service recovered"));

// Fallback: called when circuit is open
breaker.fallback(() => ({ cached: true, ...lastKnownGoodResponse }));

const result = await breaker.fire(amount, customerId);
```

## Bulkhead pattern: isolating failures

The bulkhead pattern complements circuit breakers. Instead of one connection pool for all external calls, use separate pools per downstream service. If the payment service is slow and exhausts its pool, the auth service pool is unaffected.

```javascript
const paymentQueue = new PQueue({ concurrency: 10 });
const inventoryQueue = new PQueue({ concurrency: 20 });

// Payment calls limited to 10 concurrent
const result = await paymentQueue.add(() => callPaymentService(data));
```

Circuit breakers and bulkheads are the two most important patterns for building systems that survive the inevitable failures of their dependencies.
