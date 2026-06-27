---
title: "Webhooks: receiving HTTP calls instead of making them."
description: "How webhooks work, how to implement a secure receiver, and the operational challenges involved in handling them reliably."
pubDate: 2025-07-31
tags: ["DevOps"]
draft: false
---

Most integrations follow a pull model: your application calls an API, the API returns data, your application does something with it. Webhooks reverse this. The external service calls your application when something happens. You do not poll. You listen.

## When webhooks make sense

Polling an API to check for changes is expensive and slow. If you poll every minute to detect payment status changes, you add 60 seconds of latency to every payment flow and make 1,440 API calls per day for each user.

Webhooks eliminate both problems. Stripe calls your endpoint when a payment succeeds. GitHub calls your endpoint when a push happens. Twilio calls your endpoint when an SMS is delivered. The latency is near-zero and you make zero outbound calls.

The tradeoff is that your application now needs a public HTTPS endpoint that external services can reach.

## Implementing a webhook receiver

A webhook receiver is an HTTP endpoint that accepts POST requests with a JSON body:

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
STRIPE_WEBHOOK_SECRET = 'whsec_...'

@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    # Verify the request came from Stripe
    if not verify_stripe_signature(payload, sig_header, STRIPE_WEBHOOK_SECRET):
        return jsonify({'error': 'Invalid signature'}), 400

    event = request.json
    event_type = event['type']

    if event_type == 'payment_intent.succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event_type == 'payment_intent.payment_failed':
        handle_payment_failed(event['data']['object'])

    return jsonify({'received': True}), 200

def verify_stripe_signature(payload, sig_header, secret):
    try:
        timestamp, signatures = parse_sig_header(sig_header)
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, sig) for sig in signatures)
    except Exception:
        return False
```

## Signature verification

Never process a webhook without verifying its signature. An endpoint at `POST /webhooks/stripe` is publicly accessible. Anyone can POST to it. Without verification, an attacker can trigger your payment fulfillment logic with fabricated events.

Webhook providers sign their payloads using a secret you configure during setup. The signature is sent as a header. Your receiver recomputes the signature from the raw request body and compares. If they match, the request came from the provider.

Use `hmac.compare_digest` rather than `==` for the comparison. This prevents timing attacks that could allow an attacker to guess the signature one character at a time.

Critical: compute the signature from the raw bytes of the request body, before any JSON parsing. Parsing and re-serializing JSON can change whitespace or key ordering and invalidate the signature.

## Respond fast, process async

Webhook providers have short timeouts, typically 5-30 seconds. If your endpoint takes longer to respond, the provider retries the webhook, potentially many times.

Never do slow processing synchronously in the webhook handler. Acknowledge immediately and enqueue the work:

```python
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.json
    
    # Validate signature first
    if not valid_signature(request):
        return '', 400

    # Enqueue for async processing
    job_queue.enqueue('process_stripe_event', payload)

    # Respond immediately
    return '', 200
```

The handler takes under 100ms: validate, enqueue, respond. The actual business logic runs in a background worker at whatever pace it needs.

## Idempotency in webhook handlers

Providers retry webhooks on failure. They may retry even when your endpoint returned 200, due to network issues. Your handler must be idempotent.

Use the event ID to detect duplicates:

```python
def process_stripe_event(event):
    event_id = event['id']
    
    # Check if already processed
    if ProcessedEvent.objects.filter(event_id=event_id).exists():
        return  # Already handled, skip
    
    with db.transaction():
        # Process the event
        handle_payment_succeeded(event['data']['object'])
        
        # Record that we processed it
        ProcessedEvent.objects.create(event_id=event_id)
```

The transaction ensures that if the processing fails, the event is not recorded as processed, and the next retry will run it again.

## Local development

Testing webhooks locally requires a tunnel that exposes your localhost to the internet. The Stripe CLI handles this for Stripe:

```bash
stripe listen --forward-to localhost:5000/webhooks/stripe
```

For provider-agnostic tunneling, ngrok works:

```bash
ngrok http 5000
# Gives you: https://abc123.ngrok.io
# Set this as your webhook URL in the provider's dashboard
```

## Monitoring webhook delivery

Webhook failures are silent on your end - you do not call anything, so there are no errors in your outbound request logs. Check the provider's dashboard for failed deliveries and implement alerting based on your own handler error rates.

Log every received webhook with its event type and ID before processing. If a customer reports a missed notification, you can search logs to confirm whether the webhook arrived.

Webhooks are push-based events from external systems. Treat them like any other event source: verify origin, process asynchronously, handle duplicates, and monitor for failures.
