---
title: "Multi-stage Docker builds: the technique that cuts image size by 60%."
description: "Multi-stage builds compile or bundle your application in one stage and copy only the artifacts to a minimal production image, leaving build tools and dev dependencies behind."
pubDate: 2024-10-17
tags: ["Security"]
draft: false
---

A Node.js application's production image doesn't need TypeScript, webpack, test frameworks, or build tools. But a naive Dockerfile installs everything and leaves it all in the final image. Multi-stage builds let you use multiple `FROM` instructions, keeping build tools in early stages and copying only final artifacts to a minimal production image.

## The problem with single-stage builds

A typical TypeScript application Dockerfile without multi-stage:

```dockerfile
FROM node:20
WORKDIR /app
COPY package*.json ./
RUN npm install          # installs devDependencies too
COPY . .
RUN npm run build        # TypeScript compilation
CMD ["node", "dist/server.js"]
```

This image contains:
- All devDependencies (TypeScript, ts-node, eslint, jest, ...)
- Source TypeScript files
- The full Node.js Debian base image (~350MB)
- Build caches

Result: 800MB+ image.

## Multi-stage build

```dockerfile
# Stage 1: install dependencies and build
FROM node:20-alpine AS builder

WORKDIR /app

# Install all dependencies (including devDependencies for build)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: production image
FROM node:20-alpine AS runner

RUN apk add --no-cache dumb-init

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

# Copy ONLY what's needed for production
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./

# Install ONLY production dependencies
RUN npm ci --only=production && npm cache clean --force

USER nodejs
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

The `--from=builder` instruction copies files from the `builder` stage into the `runner` stage. Everything else in the `builder` stage — the TypeScript source, devDependencies, compiler cache — is discarded. It never makes it into the final image.

Result: ~180MB instead of 800MB+. The production image contains only the Alpine base, Node, production npm dependencies, and compiled JavaScript.

## What `COPY --from` can copy

You can copy from any named stage:

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
```

Separating the dependency installation stage from the build stage is useful: if only your source code changes, Docker rebuilds the `builder` stage but can still use the cached `deps` stage.

## Copying from external images

`--from` doesn't have to reference a stage in the same Dockerfile — you can copy from any image:

```dockerfile
# Copy a compiled binary from an official image
COPY --from=golang:1.21 /usr/local/go /usr/local/go

# Copy certificates from Alpine for SSL in a scratch-based image
COPY --from=alpine:3.19 /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
```

## The scratch base image

For compiled languages (Go, Rust), the final stage can use `FROM scratch` — literally an empty filesystem:

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o server .

FROM scratch AS runner
COPY --from=builder /app/server /server
COPY --from=alpine:3.19 /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
EXPOSE 8080
CMD ["/server"]
```

A Go HTTP server in a scratch image: ~10MB. The same server with a Debian base: ~120MB. For Node.js you still need the Node runtime, but Alpine-based images are still much smaller than Debian.

## Targeting a specific stage

During development, you might want to stop at the `builder` stage to debug:

```bash
# Build only up to the builder stage
docker build --target builder -t my-app:debug .

# Run the builder stage image
docker run -it my-app:debug sh
```

This is useful for inspecting intermediate artifacts without running the full build.

## Measuring the difference

```bash
docker build -t my-app:latest .
docker images my-app
# REPOSITORY   TAG      IMAGE ID       SIZE
# my-app       latest   a1b2c3d4e5f6   178MB

# Compare with a single-stage build from your Dockerfile.single
docker build -f Dockerfile.single -t my-app:single .
docker images my-app
# my-app       single   f6e5d4c3b2a1   842MB
```

The multi-stage image pulls faster in CI and deployment pipelines, reduces storage costs, and has a smaller attack surface (fewer packages that could have vulnerabilities).
