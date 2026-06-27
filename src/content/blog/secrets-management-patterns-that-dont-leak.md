---
title: "Secrets management: the patterns that don't leak credentials."
description: "Why .env files are not enough, and the tools and patterns that keep database passwords, API keys, and certificates out of your git history."
pubDate: 2026-02-12
tags: ["Architecture"]
draft: false
---

Leaked credentials are one of the most common causes of security incidents. A database password committed to a git repo, even briefly, is compromised -- git history is forever, forks exist, and GitHub's search is thorough. Secrets management is the set of practices that keeps credentials out of places attackers can reach them.

## What goes wrong

**Secrets in code:** The most direct mistake. A connection string, API key, or private key hard-coded in source.

**Secrets in `.env` files committed to git:** `.env` files are useful locally, but if they contain real credentials and get committed, they're exposed. `.gitignore` helps, but it's easy to commit by mistake, especially when `git add .` is muscle memory.

**Secrets in CI/CD logs:** Printing environment variables in a build script exposes credentials in CI logs that may be visible to the whole organization.

**Secrets in Docker images:** Environment variables baked into a Docker image with `ENV` are readable by anyone who can pull the image.

**Secrets in Kubernetes manifests:** Kubernetes Secrets are base64-encoded by default, not encrypted. A Secret manifest committed to git is just as exposed as plaintext.

## The right approach: secrets stores

A secrets store is a dedicated service for storing and retrieving credentials. Instead of putting a database password in an environment variable at deploy time, your application fetches it from the store at startup.

**AWS Secrets Manager:**

```typescript
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";

const client = new SecretsManagerClient({ region: "us-east-1" });

async function getDbPassword(): Promise<string> {
  const response = await client.send(
    new GetSecretValueCommand({ SecretId: "prod/myapp/db-password" })
  );
  return JSON.parse(response.SecretString!).password;
}
```

The application's IAM role grants access to exactly this secret and nothing else. The password never appears in environment variables, logs, or config files.

**HashiCorp Vault** is the open-source alternative, with more flexibility: it supports dynamic credentials (generates a new database user/password per application instance, rotating automatically), secret leasing with TTLs, and audit logging of every access.

```bash
# Application fetches a dynamic database credential
vault read database/creds/myapp-role

# Returns credentials valid for 1 hour, automatically revoked after
Key                Value
username           v-myapp-xK2mP8
password           A1B2C3-...
lease_duration     1h
```

## Environment variables: safer usage

Environment variables are still the standard way to get secrets into a process. The key is where they come from:

- **Don't:** put real secrets in `.env` files committed to git
- **Don't:** set them manually in the cloud console without documentation
- **Do:** inject them from a secrets store at deploy time
- **Do:** use your cloud provider's native secrets integration (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)

For Kubernetes, use the Secrets Store CSI Driver to mount secrets from external stores directly as volumes:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-credentials
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "prod/myapp/db-password"
        objectType: "secretsmanager"
```

The pod mounts this as a volume and reads the secret as a file. It never appears in the pod spec.

## Scanning for leaked secrets

Even with good practices, mistakes happen. Automated scanning catches them:

**git-secrets** (pre-commit hook): blocks commits that match patterns like AWS key formats or private key headers.

**truffleHog**: scans git history (including all commits, not just HEAD) for high-entropy strings that look like secrets.

```bash
trufflehog git https://github.com/myorg/myrepo --only-verified
```

**GitHub Secret Scanning**: automatically scans all pushes for patterns matching known secret formats (AWS keys, Stripe keys, etc.) and notifies you immediately.

## Rotation

Static long-lived credentials are a larger target. Rotate credentials regularly:

- API keys: rotate on a schedule or when team members leave
- Database passwords: use dynamic credentials from Vault or RDS Secrets Manager auto-rotation
- TLS certificates: automate with cert-manager and Let's Encrypt

Automated rotation means a leaked credential has a limited window of validity. Combined with access logging, you can detect that a credential was used somewhere unexpected and revoke it before it causes damage.

The baseline: use `.gitignore`, `.env.example` (with fake values), a secrets store for production, and automated scanning. These four things eliminate most leaked credential incidents.
