---
title: "CQRS: separating reads and writes when they have different needs."
description: "CQRS splits your application into two models — one optimized for commands, one for queries. Here's when that separation earns its complexity."
pubDate: 2025-12-25
tags: ["Architecture"]
draft: false
---

Most applications read data far more often than they write it. Yet traditional architectures use the same model for both operations. CQRS — Command Query Responsibility Segregation — challenges that assumption by splitting the system into two explicit sides: one for commands (writes) and one for queries (reads).

## The core idea

In a standard CRUD setup, a single `Order` model handles creating orders, updating them, and fetching them for display. The problem is that what you need when writing an order (validation logic, business rules, domain invariants) is very different from what you need when reading it (joined data, aggregated counts, denormalized views for a specific UI).

CQRS says: use different models for different jobs.

```typescript
// Command side — domain-rich, focused on correctness
class PlaceOrderCommand {
  constructor(
    public readonly customerId: string,
    public readonly items: OrderItem[],
    public readonly shippingAddress: Address
  ) {}
}

class OrderCommandHandler {
  async handle(command: PlaceOrderCommand): Promise<void> {
    const customer = await this.customerRepo.findById(command.customerId);
    customer.assertCanPlaceOrder();

    const order = Order.create(command.customerId, command.items, command.shippingAddress);
    await this.orderRepo.save(order);
    await this.eventBus.publish(new OrderPlaced(order.id));
  }
}

// Query side — flat, fast, shaped for the UI
interface OrderSummary {
  id: string;
  customerName: string;
  totalAmount: number;
  itemCount: number;
  status: string;
  placedAt: Date;
}

class OrderQueryService {
  async getOrderSummaries(customerId: string): Promise<OrderSummary[]> {
    // Raw SQL or a read-optimized view — no domain objects needed
    return this.db.query(`
      SELECT o.id, c.name AS customer_name, o.total_amount,
             COUNT(oi.id) AS item_count, o.status, o.placed_at
      FROM orders o
      JOIN customers c ON c.id = o.customer_id
      JOIN order_items oi ON oi.order_id = o.id
      WHERE o.customer_id = $1
      GROUP BY o.id, c.name, o.total_amount, o.status, o.placed_at
    `, [customerId]);
  }
}
```

The command handler enforces business rules. The query service just fetches data in the shape the UI needs, with no domain model in between.

## When the read and write databases diverge

The pattern scales further when you give reads and writes separate data stores. The write side keeps a normalized, consistent database. After a command succeeds, it publishes a domain event. A projection listens for that event and updates a read model — potentially a different database entirely.

```typescript
// Event handler that keeps the read model in sync
class OrderProjection {
  async on(event: OrderPlaced): Promise<void> {
    await this.readDb.upsert('order_summaries', {
      id: event.orderId,
      customer_name: event.customerName,
      total_amount: event.totalAmount,
      item_count: event.itemCount,
      status: 'pending',
      placed_at: event.occurredAt,
    });
  }

  async on(event: OrderShipped): Promise<void> {
    await this.readDb.update('order_summaries',
      { status: 'shipped' },
      { id: event.orderId }
    );
  }
}
```

Your read model can be a Redis hash for fast lookups, a denormalized Postgres table with no joins, or an Elasticsearch index for full-text search. Each can be optimized independently.

## The consistency trade-off

Splitting read and write stores introduces eventual consistency. When a user places an order, their order list might not reflect it for a few hundred milliseconds — the time it takes for the event to propagate and the projection to update.

Most of the time this is acceptable. A few patterns help:

- **Return the written data directly** from the command response, so the UI doesn't need to refetch immediately.
- **Optimistic UI updates** — show the change locally before the read model catches up.
- **Read-your-writes** — route a user's own reads to the write database for a short window after they make a change.

## When CQRS makes sense

CQRS adds indirection. It's not the right default for a simple CRUD service. Consider it when:

- Your read patterns are significantly more complex than your write patterns (or vice versa).
- You need to scale reads and writes independently — more read replicas, different caching strategies.
- You're already using domain events and the projection pattern fits naturally.
- Your read models need to be reshaped frequently for different UIs or consumers.

A reporting dashboard that aggregates across millions of rows shouldn't go through the same code path as a form submission. CQRS gives you a principled way to separate those concerns and optimize each independently.

The pattern doesn't require a separate database from day one. Starting with a single database but distinct read and write models already delivers most of the architectural benefit, with the option to split storage later if the need arises.
