---
title: "Idempotency keys: making retries safe."
description: "What idempotency keys are, why they matter for distributed systems, and how to implement them on both the client and server side."
pubDate: 2025-07-10
tags: ["DevOps"]
draft: false
---

Networks fail. Servers restart. Load balancers time out. When a client sends a request and does not receive a response, it cannot tell whether the server processed the request successfully or not. Without idempotency, retrying the request risks duplicating a side effect: charging a customer twice, sending two confirmation emails, creating two orders.

Idempotency keys are the mechanism that makes retries safe.

## The problem in concrete terms

A user clicks "Pay" in your checkout flow. Your frontend sends a POST to `/payments`. The request reaches your server, the payment processor charges the card, but then the server crashes before sending a 200 response. The frontend receives a network error.

The user sees an error screen. Is their card charged? The frontend does not know. If it retries, and the server processes the request again, the card is charged twice.

The user calls support. Your team spends 20 minutes issuing a refund. This is a preventable problem.

## What an idempotency key is

An idempotency key is a unique identifier that the client generates and sends with the request, typically as a header. The server stores the result of processing that key. If the same key arrives again, the server returns the stored result without executing the operation a second time.

```http
POST /payments HTTP/1.1
Content-Type: application/json
Idempotency-Key: 7f3b2c9e-4a1d-4e8f-b6c3-2d1a9e4f7b3c

{
  "amount": 4999,
  "currency": "usd",
  "payment_method": "pm_abc123"
}
```

The client generates a UUID (v4) for each logical operation. If the first request fails without a clear response, the client retries with the same key. The server recognizes the key and returns the original result.

## Server implementation

The server needs a persistent store for idempotency keys mapped to their responses. Redis works well because keys can expire automatically after a reasonable window (24 hours is common).

```python
import uuid
import json
import redis
from functools import wraps
from flask import request, jsonify

cache = redis.Redis()

def idempotent(ttl=86400):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = request.headers.get('Idempotency-Key')
            if not key:
                return fn(*args, **kwargs)

            cache_key = f"idempotency:{key}"
            stored = cache.get(cache_key)

            if stored:
                data = json.loads(stored)
                return jsonify(data['body']), data['status']

            response = fn(*args, **kwargs)
            body, status = response

            cache.setex(
                cache_key,
                ttl,
                json.dumps({'body': body.get_json(), 'status': status})
            )
            return response
        return wrapper
    return decorator

@app.route('/payments', methods=['POST'])
@idempotent()
def create_payment():
    # Process payment once, safely
    result = payment_processor.charge(request.json)
    return jsonify(result), 201
```

The decorator intercepts the request, checks whether the key has been seen before, and if so returns the cached response without executing the handler function.

## Client implementation

The client generates a key per logical operation, not per HTTP request. If the same logical operation needs to be retried, the key stays the same.

```typescript
async function createPayment(amount: number, paymentMethod: string) {
  const idempotencyKey = crypto.randomUUID();

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch('/payments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({ amount, paymentMethod }),
      });

      if (response.ok) {
        return await response.json();
      }

      // 4xx errors are not retryable
      if (response.status >= 400 && response.status < 500) {
        throw new Error(`Payment failed: ${response.status}`);
      }

      // 5xx - retry with same key
    } catch (networkError) {
      if (attempt === 2) throw networkError;
      await sleep(1000 * Math.pow(2, attempt)); // exponential backoff
    }
  }
}
```

The key is generated once at the top of the function, before the loop. Every retry uses the same key.

## What must be idempotent

Not all endpoints need idempotency keys. GET requests are inherently idempotent. Reads have no side effects. The concern is with operations that create or mutate state:

- Payments and refunds
- Order creation
- Email or SMS sends
- Webhook deliveries
- Any operation that charges money, sends a notification, or creates a unique resource

## Database-level idempotency

For operations where you control the database schema, you can enforce idempotency at the database level using a unique constraint on the key:

```sql
CREATE TABLE payments (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key UUID UNIQUE NOT NULL,
  amount      INTEGER NOT NULL,
  status      TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

An insert with a duplicate `idempotency_key` will fail with a unique violation. The application catches this and returns the existing record instead of the error.

This approach is more durable than a Redis TTL because the record persists as long as the payment does, not just 24 hours. It also ties the idempotency record directly to the business object it protects.

Idempotency keys are a protocol between client and server that makes the entire request lifecycle safe to retry. Once implemented, they eliminate a whole class of support tickets.
