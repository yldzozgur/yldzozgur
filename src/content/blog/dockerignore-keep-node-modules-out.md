---
title: ".dockerignore: the file that keeps node_modules out of your image."
description: "What .dockerignore does, why it matters for build speed and image size, and what to put in it for a typical Node.js project."
pubDate: 2024-10-31
tags: ["Docker"]
draft: false
---

When Docker builds an image, the first thing it does is send your project directory to the Docker daemon as the "build context." Every file in that directory gets transferred, even if your Dockerfile never references most of them. For a Node.js project with a `node_modules` folder, that context can be hundreds of megabytes. A `.dockerignore` file tells Docker which files to leave out of the context entirely.

## What actually happens without .dockerignore

Run `docker build .` in a Node.js project without a `.dockerignore` and watch the output:

```
=> transferring context: 287.45 MB
```

That 287 MB is mostly `node_modules`. It travels from your project directory to the Docker daemon before a single line of your Dockerfile executes. On a local machine with Docker running as a process, this is still a disk-to-socket transfer. Over a remote Docker host or in CI, it is a network transfer.

Beyond the transfer cost, the bigger problem is correctness. If your `node_modules` ends up in the build context and your Dockerfile copies it into the image, you are shipping modules compiled for your development machine's OS and architecture. If you develop on macOS and deploy to Linux, native addons will fail.

## The fix: a .dockerignore file

Create `.dockerignore` in the same directory as your Dockerfile (project root). The syntax is identical to `.gitignore`.

```
node_modules
.git
.gitignore
*.md
.env
.env.*
dist
build
coverage
.nyc_output
*.log
.DS_Store
Thumbs.db
```

With this file present, Docker excludes everything listed from the build context before even looking at your Dockerfile. The `COPY . .` instruction in your Dockerfile will not include them even if the pattern would normally match.

## Why node_modules specifically

Your Dockerfile should install dependencies from scratch inside the image:

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["node", "server.js"]
```

The `RUN npm ci` step installs packages for the container's OS (Linux/Alpine). If `node_modules` were present in the build context and `COPY . .` included it, Docker might overwrite the freshly installed modules with your host's version, or the presence of the directory could cause unexpected behavior. Excluding `node_modules` via `.dockerignore` ensures the image always gets a clean, platform-appropriate install.

## Layer caching and .dockerignore work together

The `COPY package*.json ./` before `RUN npm ci` pattern exists to take advantage of Docker's layer cache. Docker caches the result of each instruction and reuses it if nothing has changed. By copying only `package.json` and `package-lock.json` first, the `npm ci` layer only re-runs when those files change. Subsequent `COPY . .` changes (your source code) do not invalidate the dependency layer.

This caching only works correctly if `node_modules` is excluded from the build context. If `node_modules` were included in the context, a change to any file inside it (which happens every time you `npm install` locally) would bust the cache for the `COPY . .` layer, even though your actual source code didn't change.

## What else belongs in .dockerignore

**`.git`**: The git directory can be large. Your running application doesn't need it. Build tooling that reads git metadata (like generating version strings from commit hashes) should use build args instead.

**`.env` files**: Environment variables should be passed in at runtime, not baked into the image. Accidentally including a `.env` file with secrets is a security issue that `.dockerignore` prevents.

**`dist` and `build`**: Local build artifacts. The image should produce its own build via `RUN npm run build`. Copying in a local build introduces the same OS/architecture problem as `node_modules`.

**Test files and coverage reports**: `*.test.js`, `*.spec.ts`, `__tests__/`, `coverage/`. Production images don't need test code.

**Documentation**: `*.md`, `docs/`. Not needed at runtime.

## Verifying what's in the build context

Two ways to check what Docker is actually including:

```bash
# Build with --no-cache and watch the context size
docker build --no-cache -t myapp .

# Use a minimal Dockerfile to list what arrives in the context
# Dockerfile.debug
FROM alpine
COPY . /context
RUN find /context -type f | sort
```

The second approach builds a throwaway image that lists every file Docker received. Compare this against what you expect to catch anything you missed in `.dockerignore`.

## A complete .dockerignore for a Node.js project

```
# Dependencies
node_modules
.npm

# Build outputs
dist
build
out
.next
.nuxt

# Test artifacts
coverage
.nyc_output
*.test.js
*.spec.js
__tests__

# Environment files
.env
.env.local
.env.*.local

# Version control
.git
.gitignore
.gitattributes

# Editor and OS files
.DS_Store
Thumbs.db
*.swp
*.swo
.vscode
.idea

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Docker files (they're already in context, but no need to copy into image)
Dockerfile*
docker-compose*
.dockerignore
```

The build context transfer that was 287 MB becomes a few kilobytes of actual source files. That time is reclaimed on every build.
