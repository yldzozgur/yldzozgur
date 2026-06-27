---
title: "Secrets in env variables: why .env is not enough and what to do instead."
description: "Environment variables are better than hardcoding secrets, but .env files have real risks. Here's the threat model and the patterns that actually protect secrets in production."
pubDate: 2024-08-01
tags: ["Security"]
draft: false
---

Environment variables are universally recommended for secrets. Most tutorials stop there. But "use environment variables" is incomplete advice — a `.env` file committed to git, logged to stdout, or world-readable on a server is no better than hardcoding the secret. Understanding the actual threats helps you apply the right protections.

## What .env files are for

`.env` files are a development convenience. The `dotenv` library reads them and populates `process.env` at startup:

```js
import "dotenv/config";

console.log(process.env.DATABASE_URL); // set from .env
```

In `.env`:
```
DATABASE_URL=postgresql://localhost:5432/myapp_dev
JWT_SECRET=dev-secret-not-used-in-production
STRIPE_SECRET_KEY=sk_test_...
```

This works fine locally. The problem is when developers treat `.env` as a security mechanism rather than a development convenience.

## The threats

**Committed to version control**: the most common mistake. A `.env` file in git history is visible to everyone with repo access, forever — even if you delete it later. The secret is in the git object database.

```bash
# .gitignore
.env
.env.local
.env.production
```

Verify it's not tracked:
```bash
git check-ignore -v .env
# should output: .gitignore:1:.env  .env
```

Even with `.gitignore`, secrets sometimes end up in git through other files — in `config.js`, hardcoded in test fixtures, printed in log output that gets committed.

**Exposed in process listings**: environment variables are visible in `/proc/<pid>/environ` on Linux and through `ps auxeww`. On a shared server, other users may be able to see your process's environment.

**Logged accidentally**: frameworks, error trackers, and APM tools sometimes serialize the entire process environment on startup or on crashes. This can send your secrets to a third-party logging service.

```js
// This logs ALL environment variables, including secrets
console.log("Server config:", process.env);

// Don't do this. Log only what you need.
console.log("Server starting on port", process.env.PORT);
```

**Leaked in error responses**: never include `process.env` in error responses sent to clients.

## Production: don't use .env files

In production, secrets should come from a secrets manager, not a file. The options:

### Platform environment variables

Cloud platforms (Heroku, Railway, Render, Fly.io, Vercel) let you set environment variables through their dashboard or CLI. These are injected at runtime without any file on disk:

```bash
# Heroku
heroku config:set JWT_SECRET=your-production-secret

# Railway
railway variables set JWT_SECRET=your-production-secret
```

The secret never touches your filesystem or codebase.

### AWS Secrets Manager / Parameter Store

For AWS deployments, store secrets centrally and retrieve them at startup:

```js
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";

async function loadSecrets() {
  const client = new SecretsManagerClient({ region: "us-east-1" });
  const response = await client.send(
    new GetSecretValueCommand({ SecretId: "prod/myapp/secrets" })
  );
  const secrets = JSON.parse(response.SecretString);
  process.env.JWT_SECRET = secrets.jwtSecret;
  process.env.DATABASE_URL = secrets.databaseUrl;
}

await loadSecrets();
```

Access is controlled by IAM roles — the EC2 instance or Lambda function is granted permission to read specific secrets, and nothing else. Rotation, versioning, and audit logging are built in.

### HashiCorp Vault

Vault is the self-hosted option for teams that need vendor-neutral secret management:

```js
import vault from "node-vault";

const client = vault({ endpoint: "https://vault.internal:8200" });
await client.token(); // authenticate via environment token

const result = await client.read("secret/data/prod/myapp");
const { jwt_secret, database_url } = result.data.data;
```

## The .env.example pattern

Keep a `.env.example` file in version control with placeholder values:

```
# .env.example — committed to git
DATABASE_URL=postgresql://localhost:5432/myapp_dev
JWT_SECRET=change-this-to-a-random-string
STRIPE_SECRET_KEY=sk_test_your_key_here
```

New developers copy this to `.env` and fill in real values. The shape of the configuration is documented; no real secrets are in git.

## Rotating secrets

One advantage of secrets managers over files: rotation without code changes. When you rotate a database password or API key, you update it in one place and every instance picks it up on next startup (or immediately with hot reload).

For `.env` files, rotation means updating every server, every developer machine, and every CI environment — and hoping nothing still has the old value cached.

The practical minimum: `.env` with `.gitignore` for local development, platform environment variables for staging and production, and a secrets manager for anything with compliance requirements or multiple rotating credentials.
