---
title: "Protocol buffers: binary serialization that's smaller and faster than JSON."
description: "Protocol Buffers encode structured data into a compact binary format. Here's how the encoding works and why it's significantly more efficient than JSON."
pubDate: 2026-05-07
tags: ["gRPC", "Performance"]
draft: false
---

JSON is readable and universal, but it carries overhead that adds up at scale: field names are repeated in every message, numbers are encoded as strings of characters, and the format has no schema enforcement. Protocol Buffers (protobuf) solve these problems with a compact binary encoding and a strict schema definition.

## The schema

Every protobuf message is defined in a `.proto` file. Field names aren't stored in the encoded data — only field numbers are.

```protobuf
syntax = "proto3";

message Order {
  string id = 1;
  string customer_id = 2;
  repeated OrderItem items = 3;
  OrderStatus status = 4;
  int64 created_at_ms = 5;
  double total_amount = 6;
}

message OrderItem {
  string product_id = 1;
  int32 quantity = 2;
  double unit_price = 3;
}

enum OrderStatus {
  PENDING = 0;
  CONFIRMED = 1;
  SHIPPED = 2;
  DELIVERED = 3;
}
```

Field numbers (the `= 1`, `= 2` parts) are what get encoded on the wire. Renaming a field in the schema has no effect on the binary format — only changing a field number is a breaking change.

## How the encoding works

Each field is encoded as a tag-value pair. The tag combines the field number and a wire type (a hint about the value's encoding).

Wire types:
- `0` — Varint (int32, int64, bool, enum)
- `1` — 64-bit (fixed64, double)
- `2` — Length-delimited (string, bytes, embedded messages, repeated fields)
- `5` — 32-bit (fixed32, float)

A varint is a variable-length integer encoding where only the bytes actually needed to represent the number are stored. Small numbers like `1` or `42` take one byte; large numbers take more. This means integer fields in practice take 1-2 bytes for typical values.

An example encoding for a small message:

```
// JSON (73 bytes):
{"id":"ord_123","quantity":5,"status":"CONFIRMED","total":49.99}

// Protobuf (approximately 20 bytes):
// Field 1 (id), wire type 2: tag=0x0a, length=7, "ord_123"
// Field 2 (quantity), wire type 0: tag=0x10, value=5
// Field 4 (status), wire type 0: tag=0x20, value=1 (CONFIRMED enum)
// Field 6 (total), wire type 1: tag=0x31, 8 bytes IEEE 754 double
```

The field name `"quantity"` doesn't appear anywhere in the binary. Neither do quotes, colons, or commas. The savings come from eliminating metadata overhead.

## Generating and using code

```bash
# Generate TypeScript types and code
protoc --plugin=protoc-gen-ts_proto --ts_proto_out=./src user.proto
```

The generated code gives you typed constructors, serializers, and deserializers:

```typescript
import { Order, OrderStatus, OrderItem } from './generated/order';

// Encode to binary
const order: Order = {
  id: 'ord_123',
  customerId: 'cust_456',
  items: [
    { productId: 'prod_789', quantity: 2, unitPrice: 24.99 },
  ],
  status: OrderStatus.CONFIRMED,
  createdAtMs: BigInt(Date.now()),
  totalAmount: 49.98,
};

const encoded: Uint8Array = Order.encode(order).finish();
console.log(encoded.byteLength); // much smaller than JSON.stringify(order).length

// Decode from binary
const decoded: Order = Order.decode(encoded);
console.log(decoded.customerId); // 'cust_456'
```

## Backward compatibility rules

Protobuf is designed for forward and backward compatibility if you follow the rules:

- **Never reuse a field number.** Old clients will try to decode a new field using the old field's type, causing corruption or parse errors.
- **New fields should be optional.** Old senders won't include them; new receivers must handle their absence.
- **Don't change a field's type.** Wire type mismatches cause decode errors.
- **Removing fields is safe** — old senders may include them; new receivers ignore unknown fields.

```protobuf
message Order {
  string id = 1;
  string customer_id = 2;
  repeated OrderItem items = 3;
  OrderStatus status = 4;
  int64 created_at_ms = 5;
  double total_amount = 6;
  // Field 7 was removed — never reuse 7 for a different field
  // optional string coupon_code = 8; // new field, safe to add
}
```

## JSON vs protobuf: when it matters

For a simple REST API handling a few hundred requests per second, the serialization format is irrelevant. The tradeoff becomes meaningful when:

- You're passing millions of messages per second through a message queue (Kafka, Pub/Sub) — smaller payloads mean lower storage and network costs.
- You have latency-sensitive service-to-service calls where even microseconds of serialization overhead accumulate.
- You need schema enforcement across a large number of producers and consumers with independent release cycles.

The cost is debuggability. A protobuf payload is opaque without the schema. JSON you can read in a log; protobuf requires tooling to inspect. For most high-volume internal systems the performance wins outweigh this cost, but it's a real operational consideration.
