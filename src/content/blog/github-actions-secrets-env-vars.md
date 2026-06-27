---
title: "GitHub Actions secrets: env variables that don't end up in your logs."
description: "How GitHub Actions secrets work, how to use them safely in workflows, and common patterns for managing sensitive configuration in CI."
pubDate: 2025-06-12
tags: ["CI/CD", "GitHub"]
draft: false
---

Hardcoding an API key in a workflow file is a fast path to a security incident. GitHub Actions has a secrets system that keeps sensitive values out of logs, out of the repository, and accessible only to authorized workflows.

## How secrets work

Secrets are encrypted at rest using libsodium. When a workflow references a secret, GitHub decrypts it just before the step runs and injects it as an environment variable. The value is masked in logs: any time the secret value appears in log output, it's replaced with `***`.

Secrets are set in three scopes:
- **Repository secrets**: Available to workflows in that repository
- **Environment secrets**: Available only to jobs targeting a specific environment (production, staging)
- **Organization secrets**: Available to selected repositories across an organization

## Setting secrets

Via the GitHub UI: Settings > Secrets and variables > Actions > New repository secret.

Via GitHub CLI:

```bash
gh secret set DATABASE_URL --body "postgres://user:pass@host/db"
gh secret set OPENAI_API_KEY --body "sk-..."

# Read from file
gh secret set PRIVATE_KEY < private_key.pem

# List secrets (names only, not values)
gh secret list
```

## Using secrets in workflow files

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy
        run: npm run deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

The `${{ secrets.SECRET_NAME }}` syntax pulls the secret value. It's only available inside `env` blocks or directly in `run` steps, not in condition expressions or job names.

## Secrets vs variables

GitHub Actions has two separate systems:

**Secrets**: Encrypted, masked in logs, suitable for passwords, API keys, certificates. Cannot be read back after setting.

**Variables**: Plaintext, visible in logs, suitable for non-sensitive configuration like feature flags, URLs, environment names.

```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}         # secret
  LOG_LEVEL: ${{ vars.LOG_LEVEL }}        # variable
  APP_NAME: ${{ vars.APP_NAME }}          # variable
```

Set variables at Settings > Secrets and variables > Actions > Variables tab.

## Environment-scoped secrets

For production deployments, use environments to add an extra approval gate:

```yaml
jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment: production  # This job uses production-scoped secrets
    steps:
      - name: Deploy to production
        run: ./deploy.sh
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

Configure the `production` environment in Settings > Environments:
- Set required reviewers (a human must approve before the job runs)
- Set deployment branches (only `main` can deploy to production)
- Add environment-specific secrets (production DATABASE_URL vs staging DATABASE_URL)

```yaml
# Deployment with environment protection
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://yourdomain.com
    steps:
      - run: echo "Deploying to production..."
```

The `url` field adds a deployment link to the GitHub PR interface.

## Handling secrets in composite actions

If you build a reusable action, secrets must be passed explicitly as inputs -- they don't inherit automatically:

```yaml
# .github/actions/deploy/action.yml
name: Deploy
inputs:
  api-key:
    description: "API key for deployment"
    required: true
runs:
  using: composite
  steps:
    - name: Deploy
      shell: bash
      run: ./deploy.sh
      env:
        API_KEY: ${{ inputs.api-key }}
```

Usage:

```yaml
- uses: ./.github/actions/deploy
  with:
    api-key: ${{ secrets.DEPLOY_API_KEY }}
```

## Preventing secret exposure

Even with masking, there are ways to accidentally leak secrets:

**Base64 encoding bypasses masking**: If you encode a secret to pass it somewhere, the encoded version is not masked.

```bash
# This will NOT be masked in logs:
echo ${{ secrets.MY_SECRET }} | base64
```

**Printing to files then echoing**: GitHub only masks the raw value, not derived forms.

**Third-party actions**: Any action you `uses` has access to environment variables. Prefer actions from verified publishers and pin to a specific commit SHA instead of a tag:

```yaml
# Safer: pinned to a specific commit
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

# Less safe: tag can be moved
- uses: actions/checkout@v4
```

## Rotating secrets

Secrets don't expire automatically. Build rotation into your process:

1. Generate a new credential
2. Update the secret via `gh secret set` or the UI
3. Verify the workflow passes with the new secret
4. Revoke the old credential

If a secret is exposed, revoke it at the source immediately, then update GitHub. Treat any exposure as a full rotation event, not just an update.
