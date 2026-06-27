---
title: "Blue-green deployments: zero-downtime releases."
description: "How blue-green deployments eliminate downtime during releases, how to implement them, and what to watch out for."
pubDate: 2025-12-01
tags: ["DevOps", "CI/CD"]
draft: false
---

Every deployment is a risk. The code might have a bug. The migration might take longer than expected. The new version might behave differently under production load. Blue-green deployments reduce this risk by keeping the old version running while the new one starts, with instant rollback capability.

## How it works

You maintain two identical production environments: Blue (currently live) and Green (idle or running the previous release).

```
Current state: Blue is live
Users → Load Balancer → Blue (v1.0, 100% traffic)
                      → Green (v0.9, 0% traffic, idle)
```

Deploy the new version to Green:

```
Deploying: Green gets the new code
Users → Load Balancer → Blue (v1.0, 100% traffic)
                      → Green (v1.1, 0% traffic, warming up)
```

Run smoke tests against Green's URL directly, without real user traffic. When ready, switch the load balancer:

```
Switched: Green is now live
Users → Load Balancer → Blue (v1.0, 0% traffic, standby)
                      → Green (v1.1, 100% traffic)
```

If something goes wrong, switch the load balancer back. Rollback takes seconds, not the minutes required to redeploy the old version.

## The database migration problem

Blue-green works cleanly for stateless code changes. It gets complicated when database schema changes are involved.

Both the old (Blue) and new (Green) versions must be able to run against the same database simultaneously -- during the window when traffic could be on either.

This means migrations must be backward compatible:

**Adding a column**: Safe. The old code ignores the new column.

```sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;
```

**Removing a column**: Unsafe. Deploy in two phases:
1. Deploy new code that doesn't read/write the column
2. Wait until old code is fully replaced
3. Then run the migration to drop the column

**Renaming a column**: Never do this in one step. Add the new column, deploy code that writes to both, migrate data, deploy code that reads from new column only, drop old column.

**Making a nullable column NOT NULL**: Add a default first, then add the constraint in a separate deploy.

The constraint: any migration you run must not break the currently running version of the code. If it does, you cannot run it during a live blue-green switch.

## Implementation with a load balancer

Nginx example with an upstream file that can be hot-reloaded:

```nginx
# /etc/nginx/conf.d/upstream.conf
upstream app {
    server blue.internal:3000;
}
```

Switch to green by updating the file and reloading nginx (no downtime with `nginx -s reload`):

```bash
cat > /etc/nginx/conf.d/upstream.conf << EOF
upstream app {
    server green.internal:3000;
}
EOF
nginx -s reload
```

For production environments, use a load balancer that supports traffic weighting for more control:

```bash
# AWS ALB: shift traffic gradually
aws elbv2 modify-listener-rule \
  --rule-arn $RULE_ARN \
  --actions '[
    {"Type":"forward","ForwardConfig":{
      "TargetGroups":[
        {"TargetGroupArn":"'$BLUE_TG'","Weight":50},
        {"TargetGroupArn":"'$GREEN_TG'","Weight":50}
      ]
    }}
  ]'
```

This allows gradual traffic shifting (10% to green, validate, then 50%, 100%) instead of a hard cut-over.

## Canary releases: traffic splitting at small scale

Canary releases are a variant: send a small percentage of traffic to the new version before committing to a full switch.

```
Users → Load Balancer → Blue (v1.0, 95% traffic)
                      → Green (v1.1, 5% traffic)
```

Monitor error rates, latency, and business metrics for the canary group. If the metrics look good, increase the percentage. If not, send all traffic back to blue.

Feature flags are a software-level canary: deploy the code to all servers but activate the feature only for a percentage of users. The deployment risk is removed from the feature-activation risk.

## Keeping two environments in sync

The blue-green model requires infrastructure for two complete environments. In the cloud, this doesn't have to mean running two full sets of servers all the time:

- Serverless functions (Vercel, Lambda) can handle this automatically -- every deployment is a new version, and traffic switches happen at the platform level
- Auto-scaling groups can be spun down when not live
- Use container orchestration (Kubernetes) with rolling deployments, which achieves similar guarantees with less infrastructure

Kubernetes rolling deployments are conceptually similar to blue-green: new pods start alongside old pods, health checks must pass before old pods are terminated, and a rollback restores the previous ReplicaSet.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0    # Never take pods below desired count
      maxSurge: 1          # Allow one extra pod during rollout
```

The goal in all cases is the same: never have a moment where no healthy version of your application is running.
