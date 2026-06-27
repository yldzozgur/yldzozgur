---
title: "Feature flags: shipping incomplete code without breaking anything."
description: "How feature flags work, the different types, and how to use them to decouple deployment from release."
pubDate: 2025-07-21
tags: ["DevOps"]
draft: false
---

The classic deployment fear: you have been working on a large feature for three weeks. It is almost done. There is one edge case left, and the UI needs a final design pass. But main is accumulating other changes that need to ship. Do you hold main, or do you ship your incomplete feature?

Feature flags break this false choice. You merge incomplete code behind a flag that is off in production. Main ships. Your feature finishes on its own schedule and goes live with a configuration change, not a deployment.

## The core concept

A feature flag is a conditional in your code that checks whether a feature is enabled before executing it. The flag state is stored in configuration, not in code.

```javascript
if (featureFlags.isEnabled('new-checkout-flow', user)) {
  return renderNewCheckout();
} else {
  return renderLegacyCheckout();
}
```

The feature ships disabled. When you are ready to release, you flip the flag on. If something goes wrong, you flip it off. No deployment required for either operation.

## Types of feature flags

**Release flags** are temporary. They wrap in-progress work during development and get removed once the feature is stable in production. Most flags should be this type.

**Experiment flags** enable A/B testing. Different users see different variants and you measure which performs better. The flag includes user cohort logic.

**Operational flags** are permanent kill switches. They control behavior in production that you want to be able to disable instantly - a new algorithm, a third-party integration, a heavy computation. These stay in the code indefinitely.

**Permission flags** gate features by user segment - beta testers, paid users, specific organizations. The flag evaluates user properties rather than a global boolean.

## Implementation from scratch

A minimal flag system needs a store and an evaluation function:

```typescript
interface FlagConfig {
  enabled: boolean;
  rolloutPercentage?: number;  // 0-100
  allowedUserIds?: number[];
}

class FeatureFlags {
  private flags: Map<string, FlagConfig>;

  constructor(config: Record<string, FlagConfig>) {
    this.flags = new Map(Object.entries(config));
  }

  isEnabled(flagName: string, userId?: number): boolean {
    const flag = this.flags.get(flagName);
    if (!flag || !flag.enabled) return false;

    // Specific user override
    if (userId && flag.allowedUserIds?.includes(userId)) return true;

    // Percentage rollout - deterministic per user
    if (flag.rolloutPercentage !== undefined && userId) {
      const hash = this.hashUserId(userId, flagName);
      return hash < flag.rolloutPercentage;
    }

    return flag.enabled;
  }

  private hashUserId(userId: number, flagName: string): number {
    // Simple deterministic hash for consistent user assignment
    const str = `${userId}-${flagName}`;
    let hash = 0;
    for (const char of str) {
      hash = ((hash << 5) - hash) + char.charCodeAt(0);
      hash |= 0;
    }
    return Math.abs(hash) % 100;
  }
}
```

The percentage rollout uses a deterministic hash of the user ID and flag name. A given user always gets the same flag state, which matters for consistent experience and reproducible debugging.

## Gradual rollouts

Releasing to 100% of users at once is the highest-risk deployment strategy. Feature flags enable gradual rollout:

```
Day 1: 1% of users  - watch error rates and metrics
Day 2: 5% of users  - expand if stable
Day 3: 25% of users - check performance impact
Day 4: 100% of users
```

If error rates spike at any stage, set the percentage back to 0. The rollback is instant and does not require code changes or deployments.

## Using a dedicated service

For anything beyond the simplest cases, use a feature flag service like LaunchDarkly, Unleash (open source), or GrowthBook. These provide:

- A UI for non-engineers to manage flags
- Audit logs of every flag change
- Targeting rules based on user attributes
- Real-time flag updates without restarting the app
- SDKs for every language

```javascript
import { LDClient } from '@launchdarkly/node-server-sdk';

const client = LDClient.init(process.env.LD_SDK_KEY);
await client.waitForInitialization();

const showNewUI = await client.variation(
  'new-checkout-flow',
  { key: user.id, email: user.email, plan: user.plan },
  false  // default value
);
```

The third argument to `variation` is the default - what to return if the flag service is unreachable. Always set this to the safe, current behavior.

## Flag hygiene

Feature flags accumulate. Every flag left in the codebase forever is technical debt. The conditional adds indirection. The test matrix doubles. Developers have to keep track of what state the flag is in.

Treat flag removal as part of completing the feature. When a feature is fully rolled out and stable, open a ticket to remove the flag and the old code path. Set a maximum lifetime on flags: if a flag has not been removed in 90 days, it gets reviewed.

Flags that control permanent kill switches or operational behavior are exempt from expiry. Name them differently to distinguish them: `ops.payment-processor-v2` vs `feature.new-checkout`.

Feature flags separate the act of merging code from the act of releasing behavior. That separation makes deployments smaller, releases safer, and rollbacks instant.
