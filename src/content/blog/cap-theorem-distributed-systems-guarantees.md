---
title: "The CAP theorem: what distributed systems can and can't guarantee."
description: "What the CAP theorem actually says, how real databases position themselves, and what this means when choosing a data store."
pubDate: 2025-12-22
tags: ["Architecture", "Databases"]
draft: false
---

The CAP theorem states that a distributed data store can provide at most two of three guarantees: Consistency, Availability, and Partition tolerance. Understanding what these words actually mean in context makes the theorem useful rather than abstract.

## The three properties

**Consistency (C)**: Every read returns the most recent write or an error. If you write a value, any subsequent read from any node in the cluster returns that value. This is linearizability -- the system behaves as if there is one copy of the data.

**Availability (A)**: Every request receives a response (not an error), though that response may not contain the most recent write. The system stays operational.

**Partition tolerance (P)**: The system continues operating when network messages between nodes are lost or delayed. A network partition is when some nodes cannot communicate with others.

## Why partition tolerance is not optional

In any distributed system deployed across multiple servers, network partitions happen. Servers fail. Network switches drop packets. Datacenter links go down. This is not a theoretical concern; it's an operational reality.

Therefore, every distributed system must tolerate partitions. The real choice is: **when a partition occurs, do you prioritize consistency or availability?**

- **CP systems**: During a partition, return an error rather than potentially stale data. The system is consistent but temporarily unavailable.
- **AP systems**: During a partition, continue serving requests with potentially stale data. The system is available but may be inconsistent.

## CP: consistency over availability

A CP system refuses to serve requests that might return stale data.

**Example**: You write "balance = $100" to the primary node. A partition occurs; the replica has "balance = $50". A CP system will not serve a read from the replica (it would return stale data) -- it returns an error or blocks until the partition resolves.

This is what you want for financial systems. A user should never see an incorrect account balance, even if that means their request temporarily fails.

**Databases in this camp**: 
- PostgreSQL with synchronous replication
- etcd, Zookeeper (consensus systems)
- MongoDB with majority write concern

## AP: availability over consistency

An AP system continues serving requests during partitions, accepting that some reads might return stale data.

**Example**: The same partition. An AP system serves the read from the replica and returns $50, even though the primary has $100. The system is available but inconsistent until the partition heals and the replica syncs.

This is acceptable for shopping carts, social media feeds, and other data where slightly stale reads are tolerable but downtime is not.

**Databases in this camp**:
- Cassandra
- CouchDB
- DynamoDB (in its default configuration)

## Where popular databases fall

| Database | Default position | Notes |
|----------|-----------------|-------|
| PostgreSQL | CP | Synchronous replication enforces consistency |
| MySQL | CP | Similar to PostgreSQL |
| MongoDB | CP (default) | Can tune toward AP with eventual consistency |
| Cassandra | AP | Eventual consistency by default, tunable quorum |
| DynamoDB | AP (default) | Eventually consistent reads by default, strongly consistent reads available at extra cost |
| Redis | Depends on config | Standalone is CA; Redis Cluster is AP |
| etcd | CP | Consensus-based, designed for configuration data |

## The PACELC extension

The CAP theorem only describes behavior during partitions. The PACELC theorem extends it to normal operation: even without a partition (P), distributed systems trade off latency (L) for consistency (C).

A CP system that blocks reads until data is confirmed across replicas is slower under normal operation. An AP system that serves from any replica is faster but may serve stale data.

PACELC captures this: PA/EL (partition tolerant/available, and in normal operation trades latency for consistency -- i.e., faster) vs PC/EC (partition tolerant/consistent, and in normal operation consistent but slower).

## What this means when choosing a database

**For financial data, inventory counts, or any data where incorrect reads cause real damage**: Use a CP database. Accept that during rare network issues, some requests fail rather than return wrong data.

**For user preferences, caches, social feeds, or data where stale reads are acceptable**: An AP database can provide better availability and lower latency by not requiring cross-replica consensus on every read.

**For most web applications**: PostgreSQL's CP guarantees with read replicas covers most cases. Strong consistency on writes, acceptable consistency for non-critical reads routed to replicas.

## Eventual consistency in practice

"Eventual consistency" means the system will converge to the same value across all nodes after the partition heals -- it just doesn't guarantee when. For DynamoDB or Cassandra, this convergence usually happens in milliseconds to seconds.

The question is whether your application can tolerate a user reading stale data for those milliseconds. If yes, eventual consistency gives you higher availability and better throughput. If no, require strong consistency, accepting the tradeoff of slightly higher latency and potential unavailability during partitions.

The CAP theorem is not a law telling you which database to use. It's a tool for understanding the tradeoffs your database is already making, so you can design your application around its actual guarantees rather than assuming guarantees that don't exist.
