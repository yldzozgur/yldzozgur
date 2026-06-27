---
title: "Event sourcing: storing what happened instead of the current state."
description: "How event sourcing works, why it gives you a complete audit log, and when the complexity is worth it."
pubDate: 2025-12-29
tags: ["Architecture"]
draft: false
---

Most applications store the current state of data. A user's balance is 240. An order's status is "shipped". You update that row and the previous value is gone. Event sourcing flips this model: instead of storing the current state, you store every event that led to it.

## The core idea

In a traditional system, you might have a `bank_accounts` table with a `balance` column. When someone deposits money, you run `UPDATE bank_accounts SET balance = balance + 100`. The previous balance is gone.

In an event-sourced system, you store events:

```
{ event: "AccountOpened",   amount: 500,  timestamp: ... }
{ event: "DepositMade",     amount: 100,  timestamp: ... }
{ event: "WithdrawalMade",  amount: 60,   timestamp: ... }
```

The current balance is derived by replaying these events. You never store 540 directly -- you compute it.

## Implementing a basic event store

An event store is simpler than it sounds. At its core it's an append-only log:

```typescript
interface DomainEvent {
  id: string;
  streamId: string;   // which aggregate this belongs to
  type: string;
  payload: unknown;
  version: number;    // sequence number within the stream
  timestamp: Date;
}

async function appendEvent(event: DomainEvent): Promise<void> {
  await db.query(
    `INSERT INTO events (id, stream_id, type, payload, version, timestamp)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [event.id, event.streamId, event.type,
     JSON.stringify(event.payload), event.version, event.timestamp]
  );
}

async function loadStream(streamId: string): Promise<DomainEvent[]> {
  const rows = await db.query(
    `SELECT * FROM events WHERE stream_id = $1 ORDER BY version ASC`,
    [streamId]
  );
  return rows.map(deserialize);
}
```

To get the current state of an account, you load its stream and fold over the events:

```typescript
function applyEvent(state: AccountState, event: DomainEvent): AccountState {
  switch (event.type) {
    case "AccountOpened":
      return { ...state, balance: event.payload.initialDeposit, open: true };
    case "DepositMade":
      return { ...state, balance: state.balance + event.payload.amount };
    case "WithdrawalMade":
      return { ...state, balance: state.balance - event.payload.amount };
    default:
      return state;
  }
}

function reconstitute(events: DomainEvent[]): AccountState {
  return events.reduce(applyEvent, { balance: 0, open: false });
}
```

## Optimistic concurrency

Without care, two concurrent writes can corrupt a stream. The `version` field solves this. When you append an event, you assert the expected version:

```sql
INSERT INTO events (stream_id, type, payload, version)
VALUES ($1, $2, $3, $4)
-- This will violate a unique constraint if another writer
-- already wrote at this version
```

Add a `UNIQUE (stream_id, version)` constraint and the database enforces that no two events share a version on the same stream. Concurrent writes fail cleanly and the application can retry.

## Projections

Raw events are useful for auditing but not for querying. You build projections (also called read models) by subscribing to the event stream and maintaining a separate, query-optimized view:

```typescript
async function rebuildBalanceSummary() {
  const events = await loadAllEvents();
  for (const event of events) {
    if (event.type === "DepositMade") {
      await db.query(
        `UPDATE account_balances SET balance = balance + $1 WHERE id = $2`,
        [event.payload.amount, event.streamId]
      );
    }
  }
}
```

Projections can be torn down and rebuilt from scratch at any time because the event log is the source of truth. This is powerful: you can add a new read model for a feature and backfill it against all historical events.

## Snapshots

Replaying thousands of events every time you load an aggregate is slow. Snapshots solve this: periodically checkpoint the current state, and on load, start from the most recent snapshot rather than event zero.

```typescript
async function loadWithSnapshot(streamId: string): Promise<AccountState> {
  const snapshot = await loadLatestSnapshot(streamId);
  const events = await loadStreamAfter(streamId, snapshot?.version ?? 0);
  return events.reduce(applyEvent, snapshot?.state ?? initialState);
}
```

## When event sourcing is worth it

Event sourcing adds complexity. You have projections to maintain, eventual consistency to reason about, and more moving parts than a simple CRUD app.

It pays off when:

- You need a complete audit log (financial systems, medical records, compliance-heavy domains)
- You need to replay history to answer questions about past states ("what did this look like on March 3rd?")
- Your domain has complex business logic where tracking what happened matters as much as what the current state is
- You're building event-driven systems where downstream services need to react to state changes

It's probably overkill for a simple CRUD application where you just need to store and retrieve data.

## The audit log you get for free

One of the biggest practical benefits: debugging. When something goes wrong, you don't have to infer what happened from the current state. You have every event, in order, with timestamps. The question "how did we get here?" becomes trivially answerable.
