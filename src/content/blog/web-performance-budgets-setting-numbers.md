---
title: "Web performance budgets: setting numbers before you regress past them."
description: "How to define performance budgets, integrate them into CI, and use them to keep Core Web Vitals from degrading over time."
pubDate: 2026-02-26
tags: ["Architecture"]
draft: false
---

Performance regressions rarely happen in one big change. They accumulate: a new image here, a heavier dependency there, an unoptimized font. Each change seems fine in isolation. Six months later, your Time to Interactive has grown from 2 seconds to 6 seconds and no one knows why.

Performance budgets set explicit limits before regression happens. A budget is a hard number: "our JavaScript bundle must not exceed 200 KB." If a PR pushes you over the limit, the build fails.

## What to budget

**Bundle size** is the most mechanical to enforce. Set a limit on the total size of JavaScript, CSS, and images for a page.

**Core Web Vitals** are the metrics Google uses for search ranking and the ones most correlated with user satisfaction:

- **LCP (Largest Contentful Paint):** time until the largest visible content element is painted. Target: under 2.5 seconds.
- **INP (Interaction to Next Paint):** responsiveness to user input. Target: under 200ms.
- **CLS (Cumulative Layout Shift):** how much the page moves around during loading. Target: under 0.1.

**Lighthouse scores** are a synthetic proxy when you can't measure real users. A CI-enforced minimum score prevents silent degradation.

## Enforcing bundle size in CI

Bundlesize and size-limit are the two main tools. `size-limit` integrates with most bundlers:

```bash
npm install --save-dev @size-limit/preset-app
```

```json
// package.json
{
  "size-limit": [
    {
      "path": "dist/bundle.js",
      "limit": "200 KB"
    },
    {
      "path": "dist/styles.css",
      "limit": "30 KB"
    }
  ],
  "scripts": {
    "size": "size-limit",
    "build": "vite build && npm run size"
  }
}
```

```bash
npm run size

  Package size limit has exceeded the limit
  dist/bundle.js: 234 KB > 200 KB limit
```

In CI, this becomes a failing step that blocks merge.

For more detail, `webpack-bundle-analyzer` or Vite's `rollup-plugin-visualizer` generates a treemap showing which dependencies are contributing what:

```typescript
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer';

export default {
  plugins: [
    visualizer({ open: true, gzipSize: true })
  ]
}
```

## Enforcing Lighthouse scores in CI

`lighthouse-ci` runs Lighthouse in CI and fails if scores drop below thresholds:

```bash
npm install --save-dev @lhci/cli
```

```yaml
# .github/workflows/perf.yml
- name: Run Lighthouse CI
  run: |
    npm run build
    npx lhci autorun

# lighthouserc.json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:3000/", "http://localhost:3000/products"]
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.8 }],
        "first-contentful-paint": ["error", { "maxNumericValue": 2000 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }]
      }
    }
  }
}
```

This runs Lighthouse against a local build and fails if performance score drops below 80 or specific metrics exceed their thresholds.

## Real user monitoring

Synthetic tests are good for CI but don't capture real user conditions. Pair CI enforcement with real user monitoring (RUM):

- **Vercel Speed Insights**: Core Web Vitals from actual visitors, broken down by page
- **Google Search Console**: field data from real Chrome users
- **web-vitals npm package**: instrument your app to send metrics to your analytics

```typescript
import { onCLS, onINP, onLCP } from 'web-vitals';

function sendToAnalytics(metric: Metric) {
  fetch('/api/metrics', {
    method: 'POST',
    body: JSON.stringify({
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      page: window.location.pathname,
    }),
  });
}

onCLS(sendToAnalytics);
onINP(sendToAnalytics);
onLCP(sendToAnalytics);
```

The combination is: CI prevents regressions before they ship, RUM tells you what real users experience after they ship. When the numbers diverge -- CI passes but RUM degrades -- you know the synthetic environment doesn't capture the real-world condition and can investigate.

Setting budgets is a one-time investment. Enforcing them in CI costs nothing to run. The value is that performance conversations shift from "let's investigate why it got slow" to "this PR exceeds the budget, here's what to cut."
