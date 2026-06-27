---
title: "Hot reload inside Docker: keeping development fast."
description: "How to get file-watching and hot module replacement working inside a Docker container using bind mounts, so you keep the benefits of containerization without losing developer speed."
pubDate: 2024-10-24
tags: ["Docker"]
draft: false
---

Running your development environment inside Docker is appealing for consistency, but the first thing developers notice is that hot reload stops working. You edit a file, nothing happens. You have to rebuild the image or restart the container manually. This defeats the purpose.

The fix is bind mounts combined with a properly configured file watcher. Here is how that works in practice.

## Why hot reload breaks in Docker

When you build an image and run it, the code inside the container is a snapshot from build time. Changes you make on your host machine are not visible inside the container because the two filesystems are separate.

The solution is to not copy code into the container at all during development. Instead, you mount your source directory from the host directly into the container. The container sees your live files, and any file watcher running inside the container can detect changes.

## Bind mounts: the core mechanism

A bind mount maps a path on your host to a path in the container. Both sides see the same files.

```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "5173:5173"
    volumes:
      - .:/app
      - /app/node_modules
```

Two volume entries here, and both matter:

- `.:/app` mounts your entire project directory into `/app` in the container.
- `/app/node_modules` is an anonymous volume that shadows the `node_modules` path from the bind mount. This prevents your host's `node_modules` (which may be built for a different OS or architecture) from overwriting the container's installed modules.

## File watching across the host/container boundary

Many file watchers use native OS filesystem events (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows). These events do not always propagate correctly across the bind mount boundary, especially on macOS and Windows where Docker runs in a Linux VM.

The fix is to enable polling in your file watcher. Most modern tools support this:

**Vite:**
```js
// vite.config.js
export default {
  server: {
    watch: {
      usePolling: true,
      interval: 300,
    },
    host: true, // required so the dev server is reachable outside the container
  },
}
```

**webpack (Create React App):**
```yaml
services:
  web:
    environment:
      - CHOKIDAR_USEPOLLING=true
      - WATCHPACK_POLLING=true
```

**Next.js:**
```js
// next.config.js
module.exports = {
  webpackDevMiddleware: config => {
    config.watchOptions = {
      poll: 300,
      aggregateTimeout: 300,
    }
    return config
  },
}
```

Polling is less efficient than native events, but at a 300ms interval the CPU overhead is negligible for most projects.

## A complete Vite + React example

```dockerfile
# Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

# Copy package files and install first (layer cache)
COPY package*.json ./
RUN npm install

# Don't copy source - it'll come from the bind mount
CMD ["npm", "run", "dev"]
```

```yaml
# docker-compose.yml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - .:/app
      - /app/node_modules
```

```json
// package.json (relevant part)
{
  "scripts": {
    "dev": "vite --host 0.0.0.0"
  }
}
```

The `--host 0.0.0.0` flag (or `server.host: true` in vite.config.js) is required. By default Vite only listens on `127.0.0.1`, which is the container's loopback. Nothing outside the container can reach it. Binding to `0.0.0.0` makes the dev server reachable through the published port.

## Separating dev and production Dockerfiles

A common mistake is trying to make a single Dockerfile serve both development and production. They have different needs. Use two files and reference them explicitly.

```
Dockerfile          # production build
Dockerfile.dev      # development only
```

```yaml
# docker-compose.yml (for development)
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
```

Your production Dockerfile runs `npm run build` and serves static files. Your dev Dockerfile just runs the dev server. Keep them separate.

## Handling new npm installs

When you run `npm install` for a new package during development, the container's `node_modules` (in the anonymous volume) is out of sync. You need to rebuild:

```bash
docker-compose down
docker-compose build
docker-compose up
```

Or more concisely:

```bash
docker-compose up --build
```

Some teams add a script for this:

```bash
# dev.sh
docker-compose down -v  # -v removes the anonymous node_modules volume
docker-compose up --build
```

The `-v` flag removes named and anonymous volumes associated with the containers, forcing a fresh `npm install` on the next build.

## Performance on macOS

macOS users may find bind mounts sluggish because Docker Desktop proxies filesystem calls through a translation layer. For large projects, consider using Docker's `delegated` or `cached` consistency options (though these are mostly deprecated in newer Docker Desktop versions), or keep your source on a case-sensitive APFS volume.

The most effective option for macOS performance today is enabling VirtioFS in Docker Desktop settings (Settings > General > VirtioFS). It uses a newer file sharing implementation that is significantly faster than the legacy osxfs.

## The result

With bind mounts and polling enabled, your workflow inside Docker matches what you'd have running the dev server directly on the host: edit a file, the watcher detects the change, the module updates in the browser. The container provides the consistent runtime environment; the bind mount provides the live code.
