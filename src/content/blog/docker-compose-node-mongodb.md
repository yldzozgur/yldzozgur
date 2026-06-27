---
title: "docker-compose for Node + MongoDB: local dev without installing anything."
description: "A complete docker-compose setup for a Node.js API and MongoDB that gives every developer an identical local environment without installing Node or MongoDB on their machine."
pubDate: 2024-10-10
tags: ["Security"]
draft: false
---

The promise of Docker for local development: every developer runs the same versions of every dependency, with no "works on my machine" problems. This is the complete setup for a Node.js API with MongoDB.

## The compose file

```yaml
# docker-compose.yml
version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev  # separate dev Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - .:/app                     # mount source for hot reload
      - /app/node_modules          # anonymous volume prevents host node_modules from overwriting container's
    environment:
      - NODE_ENV=development
      - PORT=3000
      - MONGODB_URI=mongodb://mongo:27017/myapp_dev
      - JWT_SECRET=dev-secret-not-for-production
    depends_on:
      mongo:
        condition: service_healthy  # wait for mongo to be ready
    networks:
      - app-network

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"              # expose to host for GUI tools
    volumes:
      - mongo-data:/data/db        # persist data between restarts
      - ./mongo-init:/docker-entrypoint-initdb.d  # seed scripts
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - app-network

  mongo-express:
    image: mongo-express:latest
    ports:
      - "8081:8081"
    environment:
      - ME_CONFIG_MONGODB_SERVER=mongo
      - ME_CONFIG_BASICAUTH_USERNAME=admin
      - ME_CONFIG_BASICAUTH_PASSWORD=password
    depends_on:
      mongo:
        condition: service_healthy
    networks:
      - app-network

volumes:
  mongo-data:

networks:
  app-network:
    driver: bridge
```

## The dev Dockerfile

The dev Dockerfile uses `nodemon` for hot reload instead of the production `node` command:

```dockerfile
# Dockerfile.dev
FROM node:20-alpine

# dumb-init for signal handling even in dev
RUN apk add --no-cache dumb-init

WORKDIR /app

# Copy package files and install ALL dependencies (including dev)
COPY package*.json ./
RUN npm install

ENTRYPOINT ["dumb-init", "--"]
CMD ["npx", "nodemon", "src/server.js"]
```

The production Dockerfile (named `Dockerfile`) uses `npm ci --only=production` and a multi-stage build. The dev version installs dev dependencies and uses nodemon.

## The node_modules trick

The volume mount `- .:/app` mounts your project directory into the container. This is what enables hot reload — changes on your host appear immediately inside the container.

But it creates a problem: your host machine's `node_modules` (built for your OS) would overwrite the container's `node_modules` (built for Alpine Linux). They're not compatible.

The anonymous volume `- /app/node_modules` fixes this by mounting a fresh, unnamed volume at that path. The anonymous volume takes precedence over the bind mount for that directory specifically:

```yaml
volumes:
  - .:/app               # bind mount the whole project
  - /app/node_modules    # anonymous volume "shadows" node_modules from the bind mount
```

The container uses its own `node_modules`; your host keeps its own.

## Seeding data

Place `.js` or `.sh` scripts in `./mongo-init/`. MongoDB executes them once when the container is first created (when the data volume is empty):

```js
// mongo-init/01-seed.js
db = db.getSiblingDB("myapp_dev");

db.users.insertMany([
  { email: "admin@example.com", role: "admin", createdAt: new Date() },
  { email: "user@example.com", role: "user", createdAt: new Date() },
]);

db.createCollection("posts");
```

## Common commands

```bash
# Start everything
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f app

# Rebuild after Dockerfile changes
docker compose up --build

# Open a shell in the app container
docker compose exec app sh

# Run a one-off command
docker compose run --rm app node scripts/migrate.js

# Stop everything (keep volumes)
docker compose down

# Stop and delete volumes (wipes database)
docker compose down -v
```

## Environment-specific overrides

Use `docker-compose.override.yml` for developer-specific settings that shouldn't be committed:

```yaml
# docker-compose.override.yml (in .gitignore)
services:
  app:
    environment:
      - DEBUG=myapp:*
      - SOME_DEV_ONLY_KEY=personal-value
```

Docker Compose automatically merges this with `docker-compose.yml`. Each developer can customize their local environment without touching shared files.

## Connecting from a GUI

MongoDB Compass or any MongoDB GUI connects to `localhost:27017` (the port mapped in compose). The container name `mongo` is only resolvable inside the Docker network — from your host, use `localhost`.
