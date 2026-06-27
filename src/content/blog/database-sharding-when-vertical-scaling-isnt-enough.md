---
title: "Database sharding: when vertical scaling isn't enough."
description: "Sharding partitions data across multiple database instances. Here's how the partitioning strategies work and what operational complexity they introduce."
pubDate: 2026-06-04
tags: ["Databases", "Architecture"]
draft: false
---

Most databases can be scaled vertically — larger instance, more CPU, more RAM, faster storage — and this works well up to a point. Sharding is what happens after that point: splitting data across multiple database instances so that no single instance holds the entire dataset.

## What sharding solves

A single PostgreSQL instance can handle tens of thousands of transactions per second on appropriate hardware. If your write throughput exceeds what one instance can handle, you've exhausted vertical scaling. Similarly, a dataset that's too large to fit on one server (either in storage or in memory for effective caching) benefits from horizontal partitioning.

Read load can be addressed with replicas. Write load cannot — replicas can only accept writes from the primary. Sharding distributes writes across multiple primaries.

## Sharding strategies

### Hash-based sharding

A hash function on the shard key determines which shard a row lives on.

```
shard_number = hash(shard_key) % num_shards

// Example: user data sharded by user_id
shard_0: users where hash(user_id) % 4 == 0
shard_1: users where hash(user_id) % 4 == 1
shard_2: users where hash(user_id) % 4 == 2
shard_3: users where hash(user_id) % 4 == 3
```

Data distributes evenly (assuming a good hash function) and there's no hotspot for popular keys. The problem: adding or removing shards requires rehashing and migrating a large fraction of the data.

Consistent hashing mitigates this by arranging shards on a ring — adding a shard only migrates data from its neighbors.

### Range-based sharding

Data is partitioned into contiguous ranges of the shard key.

```
shard_0: user_ids 1 - 1,000,000
shard_1: user_ids 1,000,001 - 2,000,000
shard_2: user_ids 2,000,001 - 3,000,000
```

Range-based sharding enables efficient range queries (all users in a range are on the same shard), but can create hotspots when writes cluster in a specific range — for example, when using a time-ordered ID, all new records go to the latest shard.

### Directory-based sharding

A lookup table maps keys to shards.

```
shard_lookup table:
  user_id -> shard_id
  tenant_id -> shard_id
```

Maximum flexibility — you can reassign individual keys to different shards without following a formula. The cost: the lookup table becomes a bottleneck and a single point of failure if not cached.

## Application-layer sharding

```typescript
class ShardRouter {
  private shards: DatabaseConnection[];

  constructor(shardUrls: string[]) {
    this.shards = shardUrls.map(url => new DatabaseConnection(url));
  }

  getShardForUser(userId: string): DatabaseConnection {
    // FNV-1a hash for even distribution
    const hash = fnv1a(userId);
    const shardIndex = Number(hash % BigInt(this.shards.length));
    return this.shards[shardIndex];
  }

  async getUserById(userId: string): Promise<User | null> {
    const shard = this.getShardForUser(userId);
    const result = await shard.query(
      'SELECT * FROM users WHERE id = $1', [userId]
    );
    return result.rows[0] ?? null;
  }

  async createUser(user: CreateUser): Promise<User> {
    const shard = this.getShardForUser(user.id);
    const result = await shard.query(
      'INSERT INTO users (id, email, name) VALUES ($1, $2, $3) RETURNING *',
      [user.id, user.email, user.name]
    );
    return result.rows[0];
  }
}
```

## What sharding breaks

Cross-shard queries don't exist at the database level. A query that would join two tables across different shards must be implemented in application code: query each shard separately and merge the results.

```typescript
// Scatter-gather: query all shards, merge results
async function searchUsersAcrossShards(query: string): Promise<User[]> {
  const promises = this.shards.map(shard =>
    shard.query('SELECT * FROM users WHERE name ILIKE $1 LIMIT 100', [`%${query}%`])
  );

  const results = await Promise.all(promises);
  return results.flatMap(r => r.rows);
}
```

Foreign keys across shards don't exist. Referential integrity must be enforced in application code. Distributed transactions (updating data on multiple shards atomically) require two-phase commit or saga patterns — neither is simple.

## The operational cost

Sharding multiplies your operational surface area. N shards means N databases to monitor, back up, patch, and potentially failover. Schema migrations must run across all shards in coordination. Uneven data distribution (hotspots) requires rebalancing — moving data between shards, which is complex and disruptive.

The right approach is to exhaust vertical scaling and read replicas before sharding. Most applications never need it. When they do, the complexity is the cost of handling genuine scale.
