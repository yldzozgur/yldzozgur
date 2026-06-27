---
title: "A/B testing infrastructure: the backend plumbing for controlled experiments."
description: "How to build reliable experiment assignment, the data pipeline for measuring results, and the guardrails that prevent experiments from breaking production."
pubDate: 2026-02-16
tags: ["Architecture"]
draft: false
---

Running an A/B test sounds simple: show half your users version A and half version B, measure which converts better. The product concept is simple. The engineering required to do it reliably -- consistent assignment, accurate measurement, statistical validity, and safe rollout -- is not.

## Experiment assignment

The core requirement: a user must always see the same variant. If a user in the "blue button" experiment sees a blue button on page load but a green button on refresh, you've contaminated your data and degraded the experience.

A simple, deterministic assignment function:

```typescript
import { createHash } from 'crypto';

function assignVariant(
  userId: string,
  experimentId: string,
  variants: string[],  // e.g. ['control', 'treatment']
  trafficFraction: number = 1.0
): string | null {
  // Combine userId and experimentId for isolation between experiments
  const hash = createHash('sha256')
    .update(`${userId}:${experimentId}`)
    .digest('hex');

  // Map the first 8 hex chars to a number between 0 and 1
  const bucket = parseInt(hash.slice(0, 8), 16) / 0xFFFFFFFF;

  // Return null if user isn't in the experiment
  if (bucket >= trafficFraction) return null;

  // Assign to variant based on bucket within the traffic fraction
  const variantBucket = bucket / trafficFraction;
  const index = Math.floor(variantBucket * variants.length);
  return variants[index];
}
```

This is stable (same inputs always produce the same output), fast (no database needed), and isolated (the `experimentId` salt prevents correlation across experiments -- a user in the first bucket of every experiment would skew all results).

## Feature flags as the delivery mechanism

A/B tests are most safely delivered through feature flags, not code deploys. The experiment assignment happens at request time; the code for both variants ships to production together.

```typescript
// The flag check happens at render time
const variant = assignVariant(user.id, 'checkout-button-color', ['control', 'blue']);

return (
  <CheckoutButton
    color={variant === 'blue' ? 'blue' : 'green'}
    onClick={handleCheckout}
  />
);
```

This lets you turn experiments on and off without deploys, and lets you reduce traffic to 0% instantly if something goes wrong.

## Logging exposure events

You can only measure the effect of an experiment on users who were actually exposed to it. Log an exposure event the moment a user is assigned to a variant:

```typescript
function getVariantWithExposure(
  userId: string,
  experimentId: string,
  variants: string[]
): string | null {
  const variant = assignVariant(userId, experimentId, variants);

  if (variant !== null) {
    analytics.track('experiment_exposure', {
      userId,
      experimentId,
      variant,
      timestamp: new Date().toISOString(),
    });
  }

  return variant;
}
```

Log the exposure before the user takes any action. If you only log on conversion, you've biased your denominator.

## The data pipeline

Exposures and conversions flow into an analytics pipeline. The basic query looks like:

```sql
SELECT
  e.variant,
  COUNT(DISTINCT e.user_id) AS exposed_users,
  COUNT(DISTINCT c.user_id) AS converted_users,
  COUNT(DISTINCT c.user_id)::float / COUNT(DISTINCT e.user_id) AS conversion_rate
FROM experiment_exposures e
LEFT JOIN conversions c
  ON e.user_id = c.user_id
  AND c.timestamp > e.timestamp  -- conversion after exposure
  AND c.timestamp < e.timestamp + INTERVAL '7 days'  -- within analysis window
WHERE e.experiment_id = 'checkout-button-color'
  AND e.timestamp BETWEEN '2026-02-01' AND '2026-02-15'
GROUP BY e.variant;
```

The join condition matters: the conversion must happen *after* exposure. Cross-contaminating pre-exposure behavior inflates the baseline.

## Statistical validity

Getting a statistically significant result requires:

1. **A minimum sample size**: calculated before the experiment starts based on expected effect size and desired power. Running until you see significance is p-hacking.
2. **Not peeking early**: checking results daily and stopping when significant inflates false positive rates.
3. **A pre-defined analysis window**: decide "we'll run this for two weeks" before launch.

Tools like GrowthBook, Statsig, and LaunchDarkly implement variance reduction techniques (CUPED) and sequential testing that let you check results more often with appropriate corrections.

## Guardrails

Define guardrail metrics before launch -- metrics that should not move. If your checkout experiment improves conversion but increases page errors, that's not a win. Automated monitoring on guardrails catches this:

```typescript
// Run after each day of experiment data
async function checkGuardrails(experimentId: string) {
  const metrics = await computeGuardrailMetrics(experimentId);

  for (const metric of metrics) {
    if (metric.degradation > metric.threshold) {
      await pauseExperiment(experimentId);
      await alert(`Experiment ${experimentId} paused: ${metric.name} degraded by ${metric.degradation}%`);
    }
  }
}
```

The combination of deterministic assignment, accurate exposure logging, statistical rigor, and guardrails is what separates a reliable experiment platform from a system that produces misleading results.
