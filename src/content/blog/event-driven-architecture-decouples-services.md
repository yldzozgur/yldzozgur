---
title: "Event-driven architecture: the pattern that decouples services."
description: "How event-driven architecture works, when to use it, and how to implement it with a message broker versus direct event emission."
pubDate: 2025-11-10
tags: ["Architecture"]
draft: false
---

In a synchronous system, Service A calls Service B directly and waits for a response. If Service B is slow, Service A is slow. If Service B is down, Service A fails. Event-driven architecture breaks this dependency.

## The core concept

Instead of Service A calling Service B directly, Service A publishes an event: "Something happened." Service B (and C, D, and any other interested party) subscribes to that event and reacts to it independently. Service A doesn't know who's listening or when they'll respond.

```
Synchronous:
User signup → [AuthService calls UserService] → [UserService calls EmailService] → done

Event-driven:
User signup → AuthService publishes "user.signed_up" event → done
                   ↓                            ↓
              UserService               EmailService
          (creates profile)          (sends welcome email)
```

AuthService finishes as soon as it publishes the event. The downstream effects happen asynchronously.

## Benefits and costs

**Benefits:**

- **Decoupling**: Services don't need to know about each other. AuthService doesn't import EmailService.
- **Resilience**: If EmailService is down, the event waits in the queue. When it recovers, it processes the event. AuthService was never affected.
- **Scalability**: Each consumer scales independently. If email sending is slow, scale EmailService without touching AuthService.
- **Extensibility**: Adding a new reaction to an event (e.g., "also notify the CRM") requires no changes to the publisher.

**Costs:**

- **Eventual consistency**: The downstream effects happen later, not immediately. If you need to know that the welcome email was sent before returning a response to the user, events don't help.
- **Complexity**: Debugging requires tracing events across multiple services. A synchronous call stack is easy to follow; an event chain is not.
- **Ordering**: Events may arrive out of order. Consumers must handle this.
- **Duplicate delivery**: Most message systems guarantee at-least-once delivery. Consumers must be idempotent.

## Implementation with a message broker

A message broker (RabbitMQ, Apache Kafka, AWS SQS/SNS) handles event routing, persistence, and delivery guarantees.

Publisher (using AWS SNS):

```javascript
import { SNSClient, PublishCommand } from "@aws-sdk/client-sns";

const sns = new SNSClient({ region: "us-east-1" });

async function publishUserSignedUp(userId, email) {
  await sns.send(new PublishCommand({
    TopicArn: process.env.USER_EVENTS_TOPIC_ARN,
    Message: JSON.stringify({
      type: "user.signed_up",
      userId,
      email,
      timestamp: new Date().toISOString()
    }),
    MessageAttributes: {
      eventType: { DataType: "String", StringValue: "user.signed_up" }
    }
  }));
}
```

Consumer (an SQS queue subscribed to the SNS topic):

```javascript
import { SQSClient, ReceiveMessageCommand, DeleteMessageCommand } from "@aws-sdk/client-sqs";

const sqs = new SQSClient({ region: "us-east-1" });

async function pollForEvents() {
  while (true) {
    const response = await sqs.send(new ReceiveMessageCommand({
      QueueUrl: process.env.EMAIL_QUEUE_URL,
      MaxNumberOfMessages: 10,
      WaitTimeSeconds: 20 // long polling
    }));

    for (const message of response.Messages ?? []) {
      const event = JSON.parse(JSON.parse(message.Body).Message);

      if (event.type === "user.signed_up") {
        await sendWelcomeEmail(event.email);
      }

      // Delete after successful processing
      await sqs.send(new DeleteMessageCommand({
        QueueUrl: process.env.EMAIL_QUEUE_URL,
        ReceiptHandle: message.ReceiptHandle
      }));
    }
  }
}
```

## Lightweight events without a broker

For simpler applications, an in-process event emitter handles decoupling without infrastructure:

```javascript
import EventEmitter from "events";

const eventBus = new EventEmitter();

// Publisher
async function signUpUser(email, password) {
  const user = await createUser(email, password);
  eventBus.emit("user.signed_up", { userId: user.id, email });
  return user;
}

// Consumers (registered at startup)
eventBus.on("user.signed_up", async ({ userId, email }) => {
  await sendWelcomeEmail(email);
});

eventBus.on("user.signed_up", async ({ userId }) => {
  await createUserProfile(userId);
});
```

In-process events are synchronous under the hood (they call handlers immediately) and don't survive process restarts. They're good for decoupling within a single service, not for cross-service communication.

## Idempotency: the key to handling duplicates

Most message brokers guarantee at-least-once delivery. Your event handlers will sometimes receive the same event twice. They must produce the same result regardless of how many times they process an event.

```javascript
async function sendWelcomeEmail(userId, email) {
  // Check if we already processed this
  const alreadySent = await redis.get(`welcome_email_sent:${userId}`);
  if (alreadySent) return;

  await emailService.send({ to: email, template: "welcome" });

  // Mark as sent (expires after 7 days to handle edge cases)
  await redis.setex(`welcome_email_sent:${userId}`, 604800, "1");
}
```

## Event schema evolution

Events are a public API. Once consumers depend on an event's shape, changing it breaks them. Version your events:

```json
{
  "type": "user.signed_up",
  "version": "2",
  "userId": "123",
  "email": "user@example.com",
  "plan": "pro"
}
```

Consumers check the version and handle each accordingly. Old consumers that don't understand version 2 events can ignore fields they don't recognize (forward compatibility). New consumers should handle version 1 events that lack the `plan` field (backward compatibility).

Event-driven architecture fits best when: the triggering action and its downstream effects have different latency requirements, different scaling needs, or when you want to add downstream effects without modifying the publisher.
