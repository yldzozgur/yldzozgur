---
title: "Conventional commits: the format that writes your changelog automatically."
description: "How the Conventional Commits specification works, how to enforce it with tooling, and how to generate changelogs automatically."
pubDate: 2025-06-19
tags: ["Git", "Tooling"]
draft: false
---

A changelog that nobody updates is useless. A changelog generated from commit messages is always current. Conventional Commits is the convention that makes that generation possible.

## The format

Every commit message follows a structured format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature (bumps minor version)
- `fix`: A bug fix (bumps patch version)
- `docs`: Documentation only changes
- `style`: Formatting, no logic change
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or fixing tests
- `chore`: Maintenance, dependency updates
- `ci`: Changes to CI configuration

Breaking changes are marked with `!` after the type, or with `BREAKING CHANGE:` in the footer. A breaking change bumps the major version.

Examples:

```
feat(auth): add OAuth2 login with Google

fix(api): return 404 when user not found instead of 500

feat!: drop support for Node 16

BREAKING CHANGE: Node 16 is no longer supported. Upgrade to Node 18.
```

## Why this format

The type prefix gives you machine-readable commit classification. A changelog generator can bucket commits by type, group breaking changes, and link to the full commit. Without a structured format, you're parsing free-form text.

The format also makes the git log meaningful at a glance:

```bash
git log --oneline
# a1b2c3d feat(billing): add usage-based pricing tier
# d4e5f6a fix(auth): handle expired refresh tokens
# g7h8i9j chore: update dependencies
# j1k2l3m docs: add API authentication guide
```

## Enforcing the format with commitlint

`commitlint` validates commit messages against the conventional commits spec:

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional
```

`commitlint.config.js`:

```javascript
export default {
  extends: ["@commitlint/config-conventional"]
};
```

Wire it to a git hook with Husky:

```bash
npx husky init
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
```

Now any commit that doesn't match the format is rejected:

```bash
git commit -m "fixed stuff"
# ⧗   input: fixed stuff
# ✖   subject may not be empty [subject-empty]
# ✖   type may not be empty [type-empty]
```

## Generating changelogs with release-please

Google's `release-please` is the most complete solution for conventional commits-based releases. It:
1. Reads all commits since the last release
2. Determines the next semantic version
3. Creates a PR that updates `CHANGELOG.md` and `package.json`
4. When the PR merges, creates a GitHub release with the changelog as release notes

GitHub Actions workflow:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: node
          token: ${{ secrets.GITHUB_TOKEN }}
```

That's the complete configuration. When you push to main, release-please analyzes commits since the last release tag and opens a PR with a generated changelog.

## The generated changelog format

```markdown
## [2.1.0](https://github.com/user/repo/compare/v2.0.0...v2.1.0) (2025-06-19)

### Features

* **auth:** add OAuth2 login with Google ([a1b2c3d](https://github.com/user/repo/commit/a1b2c3d))
* **billing:** add usage-based pricing tier ([e4f5g6h](https://github.com/user/repo/commit/e4f5g6h))

### Bug Fixes

* **api:** return 404 when user not found ([i7j8k9l](https://github.com/user/repo/commit/i7j8k9l))
```

Each section groups commits by type. Breaking changes get their own section at the top. Commit SHAs link to the diff.

## Alternative: standard-version

For simpler setups without GitHub integration:

```bash
npm install --save-dev standard-version
```

`package.json`:

```json
{
  "scripts": {
    "release": "standard-version",
    "release:minor": "standard-version --release-as minor",
    "release:major": "standard-version --release-as major"
  }
}
```

Running `npm run release`:
1. Bumps version in `package.json`
2. Updates `CHANGELOG.md`
3. Creates a commit and git tag

Then `git push --follow-tags` to publish.

## Scope conventions

Scopes (the optional part in parentheses) should map to areas of your codebase. Standardize them across your team:

```
feat(auth): ...
feat(billing): ...
feat(ui): ...
fix(api): ...
```

Consistent scopes let you filter the changelog by component, which is valuable for large codebases where not every release note is relevant to every reader.
