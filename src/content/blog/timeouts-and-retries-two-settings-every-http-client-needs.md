---
title: "Timeouts and retries: the two settings every HTTP client needs."
description: "Why timeouts and retries are mandatory for any HTTP client in production, how to set them correctly, and how to avoid making things worse."
pubDate: 2025-08-07
tags: ["DevOps"]
draft: false
---

An HTTP client without timeouts will hang forever if the server stops responding. An HTTP client without retries will fail on transient network errors that would have resolved if the request had been sent again. These are not edge cases. They are the normal failure modes of network communication.

## Why timeouts are mandatory

Without a timeout, a single slow upstream service can exhaust all available threads or connections in your application. Imagine a database query that usually takes 20ms. During a slow period it takes 30 seconds. Without a timeout, every request that hits that code path holds a connection for 30 seconds. Connection pool exhausted, all new requests fail immediately.

With a 2-second timeout, the slow requests fail fast and release their connections. The failure rate goes up for those requests, but the rest of the application continues functioning.

Python's requests library has no default timeout:

```python
# Bad: will hang indefinitely
response = requests.get('https://api.example.com/data')

# Good: fails in 5 seconds if no response
response = requests.get('https://api.example.com/data', timeout=5)
```

The timeout parameter in requests covers both connection establishment and reading the response. For more control, use a tuple:

```python
# 2 seconds to connect, 10 seconds to read the full response
response = requests.get(url, timeout=(2, 10))
```

In Node.js with the fetch API:

```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);

try {
  const response = await fetch(url, { signal: controller.signal });
  const data = await response.json();
  return data;
} finally {
  clearTimeout(timeoutId);
}
```

Set timeouts at every layer. If your application calls a service that calls another service, each link in the chain needs its own timeout. The outer timeout should be longer than the inner timeout, so the inner service can fail gracefully before the outer layer gives up.

## Why retries are mandatory

Networks drop packets. Servers restart. Load balancers briefly return 502 errors during deployments. These are transient failures that resolve on their own, usually within milliseconds to a few seconds.

Without retries, your application fails on every transient error. With retries, transient errors become invisible to users.

The key rule: only retry safe requests. Safe means the request has no side effect, or the side effect is idempotent. GET requests are always safe to retry. POST requests are safe to retry only if they are idempotent (see idempotency keys).

```python
import time
import requests

def request_with_retry(url, max_retries=3, backoff_factor=1):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response
            
            # 429 Too Many Requests - respect Retry-After header
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                continue
            
            # 5xx Server Error - retry
            if response.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor * (2 ** attempt))
                    continue
                raise Exception(f"Server error after {max_retries} attempts: {response.status_code}")
            
            # 4xx Client Error - don't retry, the request is wrong
            raise Exception(f"Client error: {response.status_code}")
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
                continue
            raise
```

## Exponential backoff with jitter

Retrying immediately is usually wrong. If 100 clients all fail at the same time and all retry immediately, they generate a thundering herd that hammers the recovering service.

Exponential backoff increases the wait time between retries: 1 second, 2 seconds, 4 seconds, 8 seconds. Jitter adds randomness to prevent clients from synchronizing their retries:

```python
import random

def backoff_with_jitter(attempt, base=1, cap=60):
    # Full jitter - random between 0 and the exponential value
    return random.uniform(0, min(cap, base * (2 ** attempt)))

# Attempt 0: sleep 0-1 seconds
# Attempt 1: sleep 0-2 seconds
# Attempt 2: sleep 0-4 seconds
# Attempt 3: sleep 0-8 seconds (capped at 60)
```

## What not to retry

Do not retry 4xx errors (except 429). A 400 Bad Request means the request is malformed - retrying it will produce the same 400. A 401 Unauthorized means your credentials are wrong. A 404 means the resource does not exist. Retrying these wastes time and adds load to the server.

Do not retry non-idempotent operations without idempotency keys. Retrying a payment without an idempotency key charges the card twice.

## Using a library

Writing retry logic by hand is error-prone. Libraries handle edge cases correctly:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.ConnectionError)
)
def fetch_data(url):
    return requests.get(url, timeout=5)
```

In Go, the standard `net/http` client has no built-in retry. Use a library like `hashicorp/go-retryablehttp` or wrap the client manually.

Timeouts protect your application from slow upstreams. Retries protect your application from transient failures. Both are required. Setting neither is the default. Fix that before your first on-call incident.
