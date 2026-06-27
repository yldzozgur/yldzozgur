---
title: "Never hardcode a secret. Here's how Node env variables actually work."
description: "Environment variables are the standard way to configure Node.js applications without hardcoding secrets. Here's how they work end to end."
pubDate: 2024-04-11
tags: ["Node.js"]
draft: false
---

Hardcoding a database password, API key, or JWT secret in source code is one of the most common and consequential security mistakes. Environment variables are the standard solution. Here is how they actually work in Node.js.

## How Node reads environment variables

```js
process.env.MY_SECRET // reads MY_SECRET from the environment
```

`process.env` is an object that contains all environment variables from the process's environment. You set them before starting Node:

```bash
MY_SECRET=abc123 node app.js
```

Or export them in your shell:

```bash
export DATABASE_URL="postgres://user:pass@localhost/mydb"
node app.js
```

`process.env` is always a flat object of strings. Even if you set `PORT=3000`, `process.env.PORT` is the string `"3000"`, not the number `3000`. Parse it explicitly:

```js
const port = parseInt(process.env.PORT ?? "3000", 10);
```

## .env files and dotenv

Setting variables in the shell before every run is inconvenient for development. The convention is a `.env` file in the project root:

```
# .env
DATABASE_URL=postgres://localhost/mydb
JWT_SECRET=local-dev-secret-not-for-production
PORT=3000
REDIS_URL=redis://localhost:6379
```

Load it with the `dotenv` package:

```js
require("dotenv").config();
// Now process.env has all the variables from .env
```

Node 20.6+ supports loading `.env` files natively:

```bash
node --env-file=.env app.js
```

Important: `.env` contains secrets. Add it to `.gitignore` immediately:

```gitignore
.env
.env.local
.env.*.local
```

Commit a `.env.example` with placeholder values so other developers know what to set:

```
# .env.example — commit this, not .env
DATABASE_URL=postgres://localhost/yourdb
JWT_SECRET=generate-a-random-secret
PORT=3000
```

## Validating env variables at startup

Reading `process.env` throughout the codebase without validation means missing variables cause runtime errors deep in the application. Validate all required variables at startup instead:

```js
function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

const config = {
  databaseUrl: requireEnv("DATABASE_URL"),
  jwtSecret: requireEnv("JWT_SECRET"),
  port: parseInt(process.env.PORT ?? "3000", 10),
  nodeEnv: process.env.NODE_ENV ?? "development",
};

module.exports = config;
```

Now the application fails immediately on startup with a clear error if any required variable is missing, instead of failing mysteriously when the feature is first used.

## Using zod for env validation

For more complex validation:

```js
const { z } = require("zod");

const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  PORT: z.coerce.number().default(3000),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  REDIS_URL: z.string().url().optional(),
});

const env = EnvSchema.parse(process.env);
// env.PORT is a number — zod coerced it
// env.NODE_ENV is narrowed to the enum type
```

`z.coerce.number()` handles the string-to-number conversion. The schema documents what is required and what is optional.

## Different values per environment

The pattern is: the code reads from environment variables, and the deployment environment provides the values.

Development: values in `.env`
CI: values in CI environment settings (GitHub Actions secrets, etc.)
Production: values in the hosting platform's environment config (Heroku config vars, AWS Parameter Store, etc.)

```js
// Same code, different behavior per environment
const isDev = process.env.NODE_ENV !== "production";
const logLevel = isDev ? "debug" : "warn";
```

Never have environment-specific logic that branches on a hardcoded value. Always branch on an environment variable.

## Secrets vs configuration

Not all environment variables are secrets. Separate them conceptually:

```
# Configuration (not sensitive — can be in version control in some forms)
PORT=3000
NODE_ENV=production
LOG_LEVEL=info
MAX_UPLOAD_SIZE_MB=10

# Secrets (never commit these)
DATABASE_URL=postgres://user:secret@host/db
JWT_SECRET=some-long-random-string
STRIPE_SECRET_KEY=sk_live_...
AWS_SECRET_ACCESS_KEY=...
```

Secrets should ideally be managed by a secret management service (AWS Secrets Manager, HashiCorp Vault, etc.) in production, not plain environment variables. But plain environment variables are still correct for development and far better than hardcoded values.

## Preventing leaks

```js
// Never log all environment variables
console.log(process.env); // logs your secrets

// Never include env in error responses
res.json({ error: err.message, env: process.env }); // exposes secrets to clients
```

Keep secrets out of logs and out of any data that leaves the server.
