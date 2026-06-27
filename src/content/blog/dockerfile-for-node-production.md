---
title: "A Dockerfile for a Node app that actually works in production."
description: "A production-ready Node.js Dockerfile with a non-root user, proper signal handling, layer caching optimization, and a minimal base image."
pubDate: 2024-10-07
tags: ["Security"]
draft: false
---

Most Dockerfile tutorials show the minimum to get something running. Production requires more: a non-root user for security, correct signal handling so the container stops cleanly, layer ordering for build cache efficiency, and a small final image. Here's a Dockerfile that covers all of this.

## The full Dockerfile

```dockerfile
# Use a specific version — never just "node" or "latest"
FROM node:20-alpine AS base

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Set working directory
WORKDIR /app

# Create a non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# --- Dependency layer ---
# Copy package files before source code
# This layer is cached as long as package files don't change
FROM base AS deps
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# --- Build stage (if you have a build step) ---
FROM base AS builder
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Production image ---
FROM base AS runner

# Switch to non-root user
USER nodejs

# Copy built artifacts and production dependencies
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --chown=nodejs:nodejs package.json ./

# Expose port (documentation — doesn't actually publish)
EXPOSE 3000

# Use dumb-init to wrap the process
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

## Why each piece matters

### Non-root user

Running as root inside a container is a security risk. If there's a vulnerability in your application code, an attacker running as root inside the container has more capability to break out or cause damage. Running as a non-privileged user limits the blast radius.

```dockerfile
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs
```

The `-S` flag creates a system user (no login shell, no home directory). The numeric UID/GID ensures consistent permissions if the files are accessed outside the container.

### dumb-init: proper signal handling

Node.js running as PID 1 (the init process) inside a container doesn't handle OS signals properly by default. When Docker stops a container, it sends `SIGTERM` to PID 1. If Node doesn't handle `SIGTERM`, Docker waits 10 seconds and then sends `SIGKILL` — a hard kill that can corrupt in-flight requests or database connections.

`dumb-init` runs as PID 1 and forwards signals to Node correctly:

```dockerfile
RUN apk add --no-cache dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

With `dumb-init`, your process receives `SIGTERM` and can shut down gracefully:

```js
// In your Node app
process.on("SIGTERM", async () => {
  console.log("Received SIGTERM, shutting down gracefully...");
  await server.close();
  await db.disconnect();
  process.exit(0);
});
```

### Layer caching

Docker builds layer by layer. If a layer hasn't changed, Docker reuses the cached version. Copy `package.json` before your source code so that the `npm ci` step (slow) is only re-run when dependencies change, not every time you modify a source file:

```dockerfile
# Cached unless package.json changes
COPY package*.json ./
RUN npm ci

# Not cached on source changes — runs on every rebuild, but it's fast
COPY . .
```

If you copy all source files first and then run `npm ci`, every source change invalidates the dependency cache.

### Alpine base image

`node:20-alpine` uses Alpine Linux, which is ~5MB compared to ~120MB for Debian-based images. The full `node:20-alpine` image is ~130MB; `node:20` (Debian) is ~350MB+. Smaller images pull faster, store cheaper, and have a smaller attack surface.

### Pinning the Node version

`FROM node:20-alpine` vs `FROM node:alpine`:

- `node:alpine` changes when a new major version is released — your build is non-deterministic
- `node:20-alpine` gives you the latest 20.x patch release — stable with security updates
- `node:20.11.1-alpine` pins to an exact version — maximum reproducibility

For most teams, `node:20-alpine` (patch auto-updates) is the right balance.

## Using .dockerignore

Create a `.dockerignore` file to exclude files that shouldn't be in the image:

```
node_modules
.git
.gitignore
*.md
.env
.env.*
dist
coverage
.nyc_output
```

Without this, `COPY . .` sends the entire project directory to the Docker daemon, including `node_modules` — which can be gigabytes. It also prevents accidentally including `.env` files with secrets.

## Building and running

```bash
# Build
docker build -t my-node-app:latest .

# Run
docker run -p 3000:3000 --env-file .env my-node-app:latest

# Or pass env vars individually
docker run -p 3000:3000 \
  -e DATABASE_URL=postgresql://... \
  -e JWT_SECRET=... \
  my-node-app:latest
```
