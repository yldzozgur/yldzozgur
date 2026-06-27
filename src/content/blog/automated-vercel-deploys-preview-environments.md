---
title: "Automated Vercel deploys: preview environments without any manual step."
description: "How Vercel's Git integration creates preview deployments automatically, and how to configure and control them."
pubDate: 2025-06-09
tags: ["CI-CD", "Vercel"]
draft: false
---

Every pull request gets its own URL. That's the promise of Vercel's Git integration. No branch deployments to manage, no staging environment to keep in sync. Here's how it actually works and how to configure it for production use.

## How the Git integration works

When you connect a Vercel project to a GitHub, GitLab, or Bitbucket repository, Vercel installs a webhook. Every push triggers a deployment:

- Pushes to your production branch (`main` by default) deploy to production
- Pushes to any other branch create a preview deployment at a unique URL
- Pull requests get the preview URL posted as a comment by the Vercel bot

The preview URL format is `project-name-git-branch-name-team.vercel.app`. It's stable for the lifetime of the branch -- subsequent pushes to the same branch update the same URL.

## Configuring builds with vercel.json

You control the build and deployment configuration through `vercel.json` at the project root:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm ci",
  "framework": "nextjs"
}
```

For most frameworks, you don't need this file. Vercel auto-detects Next.js, Vite, Astro, SvelteKit, and others. The file is useful when you have a non-standard build setup.

## Environment variables per environment

Vercel has three environment targets:

- **Production**: Only applied to production deployments (main branch)
- **Preview**: Applied to all preview deployments
- **Development**: For local development via `vercel env pull`

Set variables in the Vercel dashboard under Project Settings > Environment Variables, or via CLI:

```bash
vercel env add DATABASE_URL production
vercel env add DATABASE_URL preview
```

A common pattern is to use a read-only database replica for preview environments and the primary for production:

- `DATABASE_URL` (production) â†’ points to primary
- `DATABASE_URL` (preview) â†’ points to read replica or a separate preview database

Pull environment variables to your local `.env.local`:

```bash
vercel env pull .env.local
```

## Controlling which branches get deployments

By default, every branch gets a preview deployment. If you have many active branches, this can add up in build minutes. Restrict deployments in `vercel.json`:

```json
{
  "git": {
    "deploymentEnabled": {
      "main": true,
      "staging": true
    }
  }
}
```

Alternatively, use the Vercel dashboard to set ignored build step logic. The most common pattern is to only build when relevant files change:

```bash
# vercel.json - ignored build step
# Build only if src/ or package.json changed
git diff --quiet HEAD^ HEAD -- src/ package.json || exit 0
```

Set this script as the "Ignored Build Step" in Project Settings > Git. If the script exits 0, Vercel skips the build and reuses the last deployment.

## Custom domains on preview deployments

Preview deployments use Vercel's subdomain by default. You can also map a wildcard custom domain to preview branches:

1. Add `*.preview.yourdomain.com` as a domain in Vercel
2. Add a DNS wildcard CNAME: `*.preview CNAME cname.vercel-dns.com`

Vercel maps each branch to `branch-name.preview.yourdomain.com` automatically.

## Deployment protection

Preview deployments are publicly accessible by default. For private applications, enable deployment protection:

```json
{
  "protection": {
    "deploymentType": "all"
  }
}
```

This requires visitors to authenticate with their Vercel account. For external reviewers or clients, generate a bypass token:

```bash
vercel deploy --token $VERCEL_TOKEN
# or use the protection bypass secret header
```

## Deployment webhooks

Trigger external actions when a deployment succeeds. In Project Settings > Webhooks, add a webhook URL. Vercel posts a JSON payload on events like `deployment.created`, `deployment.ready`, and `deployment.error`.

Use this to:
- Notify Slack when production deploys finish
- Run post-deployment smoke tests
- Invalidate CDN caches for third-party CDNs

```javascript
// Webhook handler
app.post("/webhooks/vercel", (req, res) => {
  const { type, payload } = req.body;

  if (type === "deployment.ready" && payload.target === "production") {
    triggerSmokeTests(payload.url);
    notifySlack(`Deployed to production: ${payload.url}`);
  }

  res.sendStatus(200);
});
```

## Checking deploy status in GitHub Actions

If you have additional CI steps that should run after a Vercel deployment, use the Vercel CLI in your workflow:

```yaml
- name: Wait for Vercel deployment
  run: |
    DEPLOYMENT_URL=$(vercel ls --token ${{ secrets.VERCEL_TOKEN }} \
      --scope ${{ secrets.VERCEL_ORG_ID }} \
      | grep ${{ github.sha }} | awk '{print $2}')
    echo "DEPLOYMENT_URL=$DEPLOYMENT_URL" >> $GITHUB_ENV

- name: Run smoke tests against preview
  run: npm run test:e2e
  env:
    BASE_URL: ${{ env.DEPLOYMENT_URL }}
```

This pattern runs end-to-end tests against the actual deployed preview URL, catching issues that only appear in a deployed environment.

