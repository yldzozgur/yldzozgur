---
title: "Docker volumes: why your data disappears and how to make it persist."
description: "Containers have ephemeral storage — data written inside a container is lost when it's deleted. Volumes are how you make data survive container restarts and replacements."
pubDate: 2024-10-14
tags: ["Security"]
draft: false
---

A common Docker gotcha: you run a database container, populate it with data, stop the container, start it again — and the data is gone. Understanding why this happens and how to fix it with volumes is essential for any Docker-based development or deployment.

## Why data disappears

When you run a container, Docker creates a writable layer on top of the image's read-only layers. Anything written inside the container goes into this writable layer:

```
Container writable layer  ← your data goes here
---
Image layer 3 (COPY . .)
Image layer 2 (npm ci)
Image layer 1 (FROM node:alpine)
```

When the container is removed (not just stopped — `docker rm` or `docker run --rm`), this writable layer is deleted. The underlying image is unchanged. The data is gone.

Stopping a container (`docker stop`) preserves the writable layer. The data survives a stop/start cycle. It only disappears on removal.

This is by design: containers are meant to be stateless and replaceable. Data that needs to persist beyond a container's lifecycle should live in a volume.

## Volume types

### Named volumes

Docker manages the storage location. You refer to the volume by name:

```bash
# Create a named volume
docker volume create mongo-data

# Use it when running a container
docker run -d \
  --name mongo \
  -v mongo-data:/data/db \
  mongo:7
```

The volume persists until you explicitly delete it. You can attach the same volume to a new container after replacing the old one:

```bash
docker stop mongo && docker rm mongo

# Start a new container with the same volume — data is still there
docker run -d --name mongo -v mongo-data:/data/db mongo:7
```

In docker-compose, named volumes are declared at the top level:

```yaml
services:
  mongo:
    image: mongo:7
    volumes:
      - mongo-data:/data/db

volumes:
  mongo-data:  # declares the named volume
```

`docker compose down` stops containers but keeps volumes. `docker compose down -v` deletes volumes too.

### Bind mounts

Bind mounts map a host directory into the container. Used for development source code sharing:

```bash
docker run -d \
  -v /Users/alice/myproject:/app \  # host path : container path
  my-node-app
```

In docker-compose:

```yaml
volumes:
  - ./src:/app/src   # relative path on host
```

Changes to files on the host immediately appear in the container and vice versa. This is how hot reload works in development.

Bind mounts are not appropriate for production data — the host path must exist and be correct, and the container is coupled to the host filesystem layout.

### Anonymous volumes

Created without a name, Docker generates an ID. Survives container restarts but is deleted when the container is removed:

```yaml
volumes:
  - /app/node_modules  # anonymous volume
```

Used to exclude specific directories from bind mounts (the node_modules trick in development).

## Inspecting volumes

```bash
# List all volumes
docker volume ls

# Inspect a volume (shows the mount path on the host)
docker volume inspect mongo-data
# Output:
# "Mountpoint": "/var/lib/docker/volumes/mongo-data/_data"

# Remove a specific volume
docker volume rm mongo-data

# Remove all unused volumes
docker volume prune
```

## Finding where data is stored

Named volumes on Linux are stored at `/var/lib/docker/volumes/<name>/_data`. On Docker Desktop (Mac/Windows), they're inside the VM Docker Desktop runs, not directly accessible from the host filesystem.

To access volume data from the host on Docker Desktop, use a temporary container:

```bash
docker run --rm -v mongo-data:/data alpine ls /data
docker run --rm -v mongo-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/mongo-backup.tar.gz /data
```

## Backup and restore

```bash
# Backup: tar the volume data into a file on the host
docker run --rm \
  -v mongo-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mongo-backup.tar.gz -C /data .

# Restore: extract the backup into a fresh volume
docker volume create mongo-data-restored
docker run --rm \
  -v mongo-data-restored:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/mongo-backup.tar.gz -C /data
```

## When not to use volumes

For cloud deployments, consider whether managed databases are a better fit. Running MongoDB or PostgreSQL in a container with a volume on a single host means:
- No replication
- Backup is manual
- Volume is tied to one host — scaling horizontally is difficult

For production, managed databases (Atlas, RDS, Cloud SQL) handle replication, backup, and scaling. Docker volumes make sense for local development, testing, or simple single-server deployments.
