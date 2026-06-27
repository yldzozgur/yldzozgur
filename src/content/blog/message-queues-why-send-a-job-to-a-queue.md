---
title: "Message queues: why you'd send a job to a queue instead of handling inline."
description: "What message queues are, the problems they solve, and when adding a queue is the right architectural decision."
pubDate: 2025-08-14
tags: ["DevOps"]
draft: false
---

Some operations do not need to finish before an HTTP response is sent. Sending a welcome email, generating a report, resizing an uploaded image, processing a webhook - these are work that can happen after the response. Doing them inline makes the user wait for no benefit. Message queues are the mechanism for deferring that work.

## The problem with inline processing

A user uploads a profile photo. Your handler resizes it to four dimensions, uploads each to S3, and updates the database. This takes 3 seconds. The user stares at a loading indicator for 3 seconds waiting for the response.

The user does not need those resized images to be ready before they see a confirmation page. They need to know the upload was received. The resizing can happen in the background.

Processing inline also creates a coupling problem. If the image resizing service is slow or down, uploads fail. If you defer to a queue, uploads succeed even when downstream processing is degraded. The images queue up and process when the service recovers.

## How message queues work

A message queue is a buffer between producers (code that creates work) and consumers (code that processes work).

The producer sends a message to the queue and continues immediately:

```python
# In the web handler - fast path
@app.route('/upload', methods=['POST'])
def upload_photo():
    image_data = request.files['photo'].read()
    image_id = store_raw_image(image_data)
    
    # Queue the processing work
    job_queue.enqueue('resize_image', image_id)
    
    # Respond immediately - no waiting for resize
    return jsonify({'image_id': image_id, 'status': 'processing'}), 202
```

The consumer runs in a separate process, picks up messages, and processes them:

```python
# In a worker process
def resize_image(image_id):
    raw = load_raw_image(image_id)
    
    for size in [(thumbnail, 150, 150), (medium, 800, 600), (large, 1200, 900)]:
        name, w, h = size
        resized = resize(raw, w, h)
        upload_to_s3(resized, f"{image_id}/{name}.jpg")
    
    update_image_status(image_id, 'ready')
```

## Common queue implementations

**Redis with RQ (Python):**

```python
from redis import Redis
from rq import Queue

redis_conn = Redis()
queue = Queue(connection=redis_conn)

# Enqueue
queue.enqueue('tasks.send_welcome_email', user_id=42)

# Worker process (run separately)
# $ rq worker
```

**BullMQ (Node.js):**

```javascript
import { Queue, Worker } from 'bullmq';

const emailQueue = new Queue('emails', { connection: redisConnection });

// Producer
await emailQueue.add('welcome', { userId: 42, email: 'user@example.com' });

// Consumer (separate process)
const worker = new Worker('emails', async (job) => {
  if (job.name === 'welcome') {
    await sendWelcomeEmail(job.data.email);
  }
}, { connection: redisConnection });
```

**Celery (Python, production-grade):**

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    try:
        user = User.objects.get(id=user_id)
        mailer.send_welcome(user.email)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

## Retries and dead letter queues

Jobs fail. The email provider is down. The S3 bucket is throttling. The database is slow. A message queue handles this gracefully: on failure, the job is retried after a backoff period.

After a configurable number of retries, failed jobs move to a dead letter queue (DLQ). The DLQ is a parking lot for jobs that could not be processed. Operators can inspect failed jobs, fix the underlying problem, and replay them.

Without a DLQ, failed jobs are lost silently. With a DLQ, they are preserved for diagnosis.

## When to use a queue

Add a queue when:

- The operation is slow (external HTTP calls, image processing, report generation)
- The operation is a side effect that does not affect the response (emails, notifications, analytics events)
- The operation should survive transient failures without user action
- You need to rate-limit work against an external API
- You need to smooth out traffic spikes (jobs queue during peak load, workers drain at a steady rate)

Do not use a queue when:

- The user needs the result synchronously (they are waiting for a response that depends on the operation)
- The operation is fast and reliable (no benefit from queuing)
- The system cannot tolerate eventual processing (real-time data requirements)

## Worker scaling

Workers are independent processes. Scaling processing capacity means running more worker processes. They all pull from the same queue and coordinate automatically without any application-level orchestration.

During a traffic spike, jobs accumulate in the queue. Queue depth is a metric you can alert on and use to trigger autoscaling of worker processes.

Message queues turn your application's work into observable, retryable, scalable units. The web handler does the minimum necessary work and delegates the rest.
