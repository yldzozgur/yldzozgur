---
title: "Docker images vs containers: the mental model in 3 sentences."
description: "Developers often conflate Docker images and containers. The distinction is simple but important — getting it right makes every other Docker concept easier to understand."
pubDate: 2024-10-03
tags: ["Security"]
draft: false
---

The image/container distinction trips up nearly every developer new to Docker. Once the mental model is clear, commands like `docker run`, `docker build`, `docker ps`, and `docker images` all make immediate sense.

## The three sentences

An **image** is a read-only template — a snapshot of a filesystem and configuration, stored on disk. A **container** is a running instance of an image — an isolated process with its own filesystem, network, and process space. The relationship is the same as between a class and an object: the image is the class, the container is the instantiated object.

## What this means in practice

You can run multiple containers from the same image:

```bash
# Same image, three separate containers
docker run -d --name web1 -p 3001:3000 my-node-app:latest
docker run -d --name web2 -p 3002:3000 my-node-app:latest
docker run -d --name web3 -p 3003:3000 my-node-app:latest
```

Each container has its own filesystem (a copy-on-write layer on top of the image), its own process, and its own state. Changes inside one container don't affect the others and don't affect the underlying image.

## Exploring the difference with commands

```bash
# Images on disk
docker images
# REPOSITORY      TAG       IMAGE ID       SIZE
# my-node-app     latest    a1b2c3d4e5f6   182MB
# mongo           7         f1e2d3c4b5a6   695MB
# node            20-alpine  0a1b2c3d4e5f  132MB

# Running containers (instances of images)
docker ps
# CONTAINER ID   IMAGE           STATUS     NAMES
# 9a8b7c6d5e4f   my-node-app     Up 2 min   web1
# 3f2e1d0c9b8a   mongo:7         Up 2 min   db

# All containers, including stopped ones
docker ps -a
# Shows stopped containers too — they still exist, just not running
```

A stopped container still exists. Its filesystem layer is preserved. You can restart it with `docker start <name>`.

## Images are built; containers are run

```bash
# Build creates an image from a Dockerfile
docker build -t my-node-app:latest .

# Run creates a new container from the image
docker run my-node-app:latest

# The image remains after the container exits
docker ps -a        # container shows as Exited
docker images       # image still there
```

By default, containers persist after they exit. Use `--rm` to delete the container automatically when it stops — useful for short-lived tasks:

```bash
docker run --rm my-node-app:latest node scripts/seed.js
# Container deleted when the script finishes
```

## Layers: how images are structured

An image is not a single file — it's a stack of layers. Each instruction in a Dockerfile creates a layer:

```dockerfile
FROM node:20-alpine        # layer 1: base OS + Node
WORKDIR /app               # layer 2: set working dir
COPY package*.json ./      # layer 3: copy package files
RUN npm ci                 # layer 4: install dependencies
COPY . .                   # layer 5: copy source code
CMD ["node", "server.js"]  # metadata: default command
```

Layers are content-addressed and shared between images. If two images both start from `node:20-alpine`, Docker stores that layer once. This is why pulling related images is fast — shared layers are already cached.

When you run a container, Docker adds a thin writable layer on top of the image's read-only layers. This writable layer captures any files created or modified inside the container. When the container is deleted, this layer is deleted. The underlying image is unchanged.

## Persisting data

Because the container's writable layer is deleted with the container, any data written inside the container disappears. Use volumes for data that should persist:

```bash
docker run -d \
  --name db \
  -v mongo-data:/data/db \   # named volume: persists beyond container lifecycle
  mongo:7
```

The volume exists independently of any container. Delete and recreate the container with the same volume mount and the data is still there.

This is the practical implication of the image/container model: the application (image) and its state (volumes) are separate concerns. You can upgrade the application by pulling a new image and starting a new container with the same volume.
