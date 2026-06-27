---
title: "Preview deployments: every PR reviewable without a meeting."
description: "How preview deployments work, why they replace synchronous review sessions, and how to set them up with modern CI pipelines."
pubDate: 2025-06-30
tags: ["DevOps"]
draft: false
---

Every time a developer opens a pull request, their changes exist in a vacuum. Reviewers read the diff, try to mentally simulate the behavior, and often schedule a meeting or screen share to see it running. Preview deployments break that cycle by giving every PR its own live URL.

## What a preview deployment is

A preview deployment is a fully functional, isolated instance of your application deployed automatically when a PR is opened or updated. It is not a staging environment shared by the whole team - it is per-branch and ephemeral. When the PR closes, the deployment is torn down.

The URL typically encodes the branch name or PR number, like `https://my-app-pr-42.preview.example.com`. Anyone with the link can open a browser and interact with the exact code under review.

## How it works mechanically

The CI pipeline does the work. A typical setup using GitHub Actions and a platform like Vercel, Netlify, or Render looks like this:

```yaml
name: Preview Deploy

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Deploy preview
        run: |
          vercel --token ${{ secrets.VERCEL_TOKEN }} \
                 --yes \
                 --env NODE_ENV=preview \
          > deployment-url.txt

      - name: Comment PR with URL
        uses: actions/github-script@v7
        with:
          script: |
            const url = require('fs').readFileSync('deployment-url.txt', 'utf8').trim();
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `Preview deployed: ${url}`
            });
```

The pipeline checks out the branch, builds it, deploys it to an isolated environment, and posts the URL as a PR comment. From that point on, every push to the branch redeploys to the same preview URL.

## Environment isolation

A useful preview deployment needs its own data, not shared state with staging. There are two common approaches.

The first is a seed database. On deploy, a script runs that creates a fresh database and loads fixture data. The app boots against that database. Any writes during review are contained to that instance.

The second is a feature-flagged slice of a shared database. The preview app reads and writes to namespaced rows, identified by a branch-specific key injected as an environment variable at deploy time. This avoids the overhead of database provisioning but requires discipline to keep namespacing consistent.

For most teams starting out, the seeded database approach is simpler and more reliable.

## What this replaces

Without preview deployments, the review process looks like this: the reviewer reads a diff, has questions, schedules a call, the author shares their screen, both people block out 30 minutes. This is expensive.

With preview deployments, the reviewer opens the link, clicks through the changed flow, leaves a comment. The asynchronous loop works. Time zones stop mattering. Reviewers in different offices can review without coordination overhead.

Design reviews benefit especially. Pixel-level feedback is impossible from a diff. "The button looks off" is not something you can say from reading JSX. Seeing the rendered UI makes design feedback specific and actionable.

QA passes can happen before merge rather than after. A tester can verify acceptance criteria against the preview URL, add a checkmark comment, and the PR gets merged knowing the feature was validated.

## Practical tips

Keep build times short. A preview that takes 12 minutes to deploy defeats the asynchronous advantage. Use caching aggressively - cache `node_modules`, cache build artifacts, cache Docker layers. Aim for under 3 minutes from push to live URL.

Set environment-specific feature flags. Preview environments should behave like production but may need third-party integrations swapped for stubs. A `PREVIEW=true` environment variable lets you short-circuit email sending, payment processing, and other side effects that should not fire against test data.

Add a visual banner. Inject a small DOM element when `PREVIEW=true` is set, showing the branch name and commit SHA. Reviewers know immediately which version they are looking at and can confirm after a redeploy that they are on the latest build.

Protect preview URLs if the repository is public. Basic auth or a preview-specific API key prevents search engines and external parties from indexing or interacting with ephemeral instances.

Preview deployments are infrastructure, not a luxury. Once a team ships them, going back feels as painful as giving up CI itself.
