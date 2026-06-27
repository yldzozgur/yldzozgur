---
title: "Container networking: how two containers find each other by name."
description: "A practical look at Docker networks, DNS resolution between containers, and why your API container can't reach 'localhost' from inside another container."
pubDate: 2024-10-21
tags: ["Docker"]
draft: false
---

When you run two containers and try to make them talk to each other, the first instinct is to use `localhost`. It doesn't work. Understanding why requires a quick mental model of how Docker handles networking.

## Each container has its own network namespace

A Docker container is, among other things, a separate network namespace. That means `localhost` inside container A refers to container A's loopback interface, not the host machine and certainly not container B. They are isolated by design.

The way containers find each other is through Docker's built-in DNS resolver, which only works when containers are on the same user-defined network.

## The default bridge network vs user-defined networks

Docker creates a default bridge network automatically. If you run two containers without specifying a network, they both end up on this default bridge. The problem: the default bridge does not support DNS-based service discovery. Containers can communicate by IP address, but those IPs are assigned dynamically and change every time a container restarts.

User-defined bridge networks are different. When you create your own network, Docker automatically provides a DNS server that resolves container names (and service names in Compose) to their current IP addresses. This is the mechanism that makes `http://api:3000` work from inside a frontend container.

```bash
# Create a network
docker network create myapp

# Start a backend container on that network
docker run -d --name api --network myapp my-api-image

# Start a frontend container on the same network
docker run -d --name frontend --network myapp my-frontend-image

# From inside frontend, this now resolves:
curl http://api:3000/health
```

## How docker-compose handles this automatically

When you define services in a `docker-compose.yml`, Compose creates a user-defined network for the entire project by default. Every service automatically joins it, and every service name becomes a resolvable hostname.

```yaml
services:
  api:
    build: ./api
    ports:
      - "3000:3000"

  web:
    build: ./web
    environment:
      - API_URL=http://api:3000
    depends_on:
      - api
```

Here, the `web` container can reach the `api` container using the hostname `api`. Docker's embedded DNS translates that name to whatever IP the `api` container currently has. If you restart just the `api` container, it may get a new IP, but the DNS entry updates and `web` never notices.

## Exposing ports vs linking containers

There is a distinction worth being explicit about:

- **`ports`** maps a container port to the host machine. It makes the service reachable from outside Docker (your browser, curl on the host, another machine on the network).
- Container-to-container traffic on the same Docker network does not go through the host's port mapping at all. The `api` container's port `3000` is directly reachable by `web` without any `ports` declaration.

This means you can keep internal services unexposed to the host while still having them talk freely to each other.

```yaml
services:
  db:
    image: postgres:16
    # No 'ports' here - the database is not reachable from your laptop
    environment:
      POSTGRES_PASSWORD: secret

  api:
    build: ./api
    ports:
      - "3000:3000"  # Only the API is exposed to the host
    environment:
      DATABASE_URL: postgres://postgres:secret@db:5432/mydb
```

## Inspecting the network to debug issues

When container-to-container communication breaks, the first tools to reach for:

```bash
# See which containers are on a network and their assigned IPs
docker network inspect myapp

# From inside a running container, test DNS resolution
docker exec -it frontend sh
nslookup api
ping api

# Check if a specific port is reachable
docker exec -it frontend sh -c "nc -zv api 3000"
```

If `nslookup api` fails, the containers are not on the same network. If it resolves but the connection is refused, the service is not listening or is crashing on startup.

## Multiple networks for isolation

You can attach a container to more than one network. This is useful when you want some services to be able to talk to each other but not to the rest of the stack.

```yaml
services:
  api:
    build: ./api
    networks:
      - frontend-net
      - backend-net

  web:
    build: ./web
    networks:
      - frontend-net

  db:
    image: postgres:16
    networks:
      - backend-net

networks:
  frontend-net:
  backend-net:
```

In this layout, `web` can reach `api`, `api` can reach `db`, but `web` cannot reach `db` directly. The database is invisible to the frontend network.

## The practical summary

Use user-defined networks (which Compose gives you automatically). Reference other services by their service name as the hostname. Reserve `ports` for services that need to be reachable from outside Docker. When something breaks, `docker network inspect` and `nslookup` from inside the container are your first two moves.
