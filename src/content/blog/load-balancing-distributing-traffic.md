---
title: "Load balancing: distributing traffic without a single point of failure."
description: "How load balancers distribute traffic across server instances, the algorithms they use, and how health checks keep traffic away from failed instances."
pubDate: 2025-11-27
tags: ["DevOps", "Architecture"]
draft: false
---

A single server is a single point of failure. When it goes down, everything goes down. A load balancer distributes traffic across multiple server instances, so no single instance is critical and capacity can grow by adding instances.

## What a load balancer does

A load balancer sits in front of your application servers. Every request hits the load balancer, which selects a backend server and forwards the request. The response comes back through the load balancer (or directly from the server, depending on configuration).

```
Client → Load Balancer → [Server 1]
                       → [Server 2]
                       → [Server 3]
```

The client talks to one IP address (the load balancer). The load balancer handles routing.

## Algorithms

**Round Robin**: Each request goes to the next server in sequence. Simple, works well when all servers have similar capacity and request processing times are similar.

```
Request 1 → Server 1
Request 2 → Server 2
Request 3 → Server 3
Request 4 → Server 1
...
```

**Weighted Round Robin**: Some servers get more traffic based on their weight. Use when servers have different capacities:

```
Server 1 (weight 3): 3 out of every 5 requests
Server 2 (weight 2): 2 out of every 5 requests
```

**Least Connections**: Each request goes to the server with the fewest active connections. Better than round-robin when requests have highly variable processing times -- a fast request and a slow request both count as one in round-robin.

**IP Hash**: The client's IP address determines which server handles their requests. The same client always goes to the same server. This provides session stickiness without session storage on the load balancer.

**Least Response Time**: Track average response time per server; send to the fastest. More complex to implement but optimal when server performance varies.

## Health checks

A load balancer that routes to a failed server makes things worse. Health checks detect failures and remove unhealthy instances from rotation.

Two types:

**Passive health checks**: The load balancer monitors actual traffic. If a server returns 5xx errors above a threshold, or times out, it's marked unhealthy and removed.

**Active health checks**: The load balancer sends periodic probe requests to each server:

```
GET /health HTTP/1.1
Host: server1.internal
```

Your server responds:

```javascript
app.get("/health", async (req, res) => {
  try {
    await db.query("SELECT 1"); // check database connectivity
    res.json({ status: "ok", timestamp: Date.now() });
  } catch (error) {
    res.status(503).json({ status: "error", error: error.message });
  }
});
```

A 200 response means healthy. A 5xx or timeout means unhealthy. The load balancer stops sending traffic to unhealthy instances and re-checks periodically to restore them.

Health check design matters: check what actually matters (can the server process requests?) not just whether the process is running.

## Session stickiness (sticky sessions)

If your application stores session state in memory (not in a shared cache), requests from the same user must go to the same server. Otherwise, the session is lost.

The right fix: store sessions in Redis or a database, not in-memory. Then any server can handle any request.

If you must use sticky sessions:

- **Cookie-based**: The load balancer sets a cookie identifying which server to use. Future requests with that cookie go to the same server.
- **IP hash**: Client IP determines the server (breaks when clients share IPs or IPs change).

Sticky sessions introduce a problem: if the pinned server goes down, all users assigned to it lose their session. Session state in a shared store is more resilient.

## Layer 4 vs Layer 7 load balancing

**Layer 4 (transport layer)**: Routes based on IP and TCP port. Fast, low overhead. Cannot inspect the request content.

**Layer 7 (application layer)**: Routes based on HTTP content -- URL path, headers, cookies, request body. More flexible:

```nginx
# nginx Layer 7 routing
upstream api_servers {
    server api1.internal:3000;
    server api2.internal:3000;
}

upstream static_servers {
    server static1.internal:3000;
    server static2.internal:3000;
}

server {
    location /api/ {
        proxy_pass http://api_servers;
    }
    location / {
        proxy_pass http://static_servers;
    }
}
```

This routes API traffic to one pool and static content to another. Layer 7 also enables SSL termination (decrypting HTTPS at the load balancer, communicating to backends over HTTP on the internal network).

## Nginx as a load balancer

```nginx
upstream backend {
    least_conn; # algorithm

    server backend1.example.com:3000;
    server backend2.example.com:3000;
    server backend3.example.com:3000;

    keepalive 32; # persistent connections to backends
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }
}
```

`X-Real-IP` and `X-Forwarded-For` preserve the client's original IP address, since from the backend server's perspective all requests come from the load balancer.

## Cloud load balancers

AWS Application Load Balancer (ALB), Google Cloud Load Balancing, and Azure Load Balancer are managed services that handle:
- Automatic health checks
- SSL termination
- Auto-scaling group integration
- Geographic routing
- DDoS protection

For most applications on cloud infrastructure, managed load balancers are the right choice. They're cheaper, more reliable, and require less operational work than running your own.
