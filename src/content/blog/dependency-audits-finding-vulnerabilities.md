---
title: "Dependency audits: finding vulnerabilities before they become your problem."
description: "How npm audit works, what the output means, and a practical workflow for keeping your dependency tree clean."
pubDate: 2026-01-12
tags: ["Architecture"]
draft: false
---

Your application has a lot of code you didn't write. The average Node.js project has hundreds of transitive dependencies -- packages that your direct dependencies depend on. Each one is a potential attack surface, and vulnerabilities in them are regularly discovered. `npm audit` exists to surface those vulnerabilities before they surface in a breach.

## What npm audit does

`npm audit` compares your installed packages against the npm security advisory database. It reports:

- Package name and affected version range
- Severity (critical, high, moderate, low)
- A description of the vulnerability
- Whether a fix is available and what version it's in

```bash
npm audit
```

```
# npm audit report

lodash  <4.17.21
Severity: high
Prototype Pollution - https://npmjs.com/advisories/1523
fix available via `npm audit fix`
node_modules/lodash
  some-package  *
  Depends on vulnerable versions of lodash
  node_modules/some-package

3 vulnerabilities (1 moderate, 2 high)
```

The output groups vulnerabilities by affected package and traces back through the dependency tree to show you which of your direct dependencies pulls them in.

## npm audit fix

For many vulnerabilities, npm can fix them automatically:

```bash
npm audit fix
```

This upgrades packages to the minimum version that resolves the vulnerability, staying within the semver ranges specified in your `package.json`. If an upgrade requires a MAJOR version bump (potentially breaking), `npm audit fix` won't apply it by default.

To force major upgrades:

```bash
npm audit fix --force
```

Use `--force` carefully. It may upgrade packages beyond your specified ranges and introduce breaking changes. Test thoroughly after running it.

## Reading the JSON output

For scripting or CI, the JSON output is more useful:

```bash
npm audit --json
```

The exit code is also meaningful: 0 means no vulnerabilities, non-zero means vulnerabilities were found. This makes it easy to fail a CI job:

```yaml
# .github/workflows/security.yml
- name: Security audit
  run: npm audit --audit-level=high
```

`--audit-level` sets the minimum severity that causes a non-zero exit. `--audit-level=high` fails on high and critical vulnerabilities but ignores moderate and low.

## Triaging what matters

Not all vulnerabilities require immediate action. Ask:

**Is the vulnerable code path reachable?** A vulnerability in a package used only in tests is lower priority than one in production code. A server-side prototype pollution vulnerability doesn't matter if you sanitize all inputs.

**Is it actually exploitable in your context?** An advisory might describe a vulnerability that requires the attacker to control a specific input that you never expose.

**Is a fix available?** If no fix exists, your options are to find an alternative package, implement a workaround, or accept the risk.

## Ignoring known false positives

When you've triaged a vulnerability and decided to accept it, document that decision. npm doesn't have a built-in ignore mechanism, but you can use `.nsprc` or audit-level flags. For team-level auditing, tools like `audit-ci` let you define allowlists:

```json
// audit-ci.json
{
  "high": true,
  "allowlist": ["GHSA-xxxx-yyyy-zzzz"]
}
```

```bash
npx audit-ci --config audit-ci.json
```

This fails on high vulnerabilities except for the listed advisory IDs, where you've made a deliberate decision.

## Keeping up with new advisories

A clean audit today doesn't mean a clean audit tomorrow. New vulnerabilities are published regularly. Automate the check:

**Dependabot** (GitHub): automatically opens PRs when security vulnerabilities are found in your dependencies.

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**Renovate**: similar to Dependabot but more configurable, supports monorepos, and can group updates.

**npm audit in CI**: run `npm audit` in every CI build so new vulnerabilities don't go unnoticed between Dependabot checks.

## Beyond npm audit

`npm audit` only covers packages in the npm advisory database. For broader coverage:

- **Snyk**: scans npm, GitHub, and your container images. Has a free tier.
- **Socket.dev**: analyzes package behavior, not just known CVEs. Catches malicious packages before they get a CVE.
- **OWASP Dependency-Check**: useful if you have Java or Python dependencies alongside Node.

The process: run `npm audit` regularly, triage what matters, fix what you can, document what you're accepting, and automate so you don't have to remember. Dependency vulnerabilities are a solved problem if you stay on top of them. They become a crisis when you ignore them for months.
