# Content calendar — 2 months / 16 posts

**Window:** 2026-05-19 → 2026-07-09 (8 weeks, 2 posts/week)
**Cadence:** Tuesday + Thursday, 10:00 Central
**Total:** 16 posts across two tracks

---

## Identity rule (CRITICAL — applies to titles, slugs, body)

**Never use:**
- ❌ Years of experience claims ("six years of Java", "my first 200-line PR", "after three years of...")
- ❌ Current or past employer names (Ameza Solutions, Ebebek, Lactalis, Gaga, any client)
- ❌ Personal location (Austin, Texas, Turkey, Boston)
- ❌ Visa/immigration status
- ❌ Career history specifics (Clarusway, MBA dates, ESL program, relocation year)
- ❌ Personal milestones ("two months of writing", "my first PR", "I just graduated")
- ❌ Junior / senior framing in titles ("what bootcamp didn't teach me", "for juniors trying to break in")

**Why:** the public site, GitHub README, and blog stay **topic-first, not biography-first**. Career history is recruiter-only — lives on LinkedIn and the CV PDF. Random readers should leave knowing the topic, not the author's resume.

**Voice in body copy:**
- Technical, educational, evergreen.
- Use "I" only to illustrate a concrete technical decision in the middle of an explanation ("I'd pick X when Y because Z"). Never as a credibility claim.
- The reader cares about the idea. Make the idea the subject of the sentence.
- Examples will use generic project shapes ("a Node REST API", "a React dashboard"), not named projects or clients.

**Title formula that works:**
- `[Technology] — [problem] / [pattern] / [trade-off]`
- `[Library A] vs [Library B] — [decision dimension]`
- `Why [pattern] / When [pattern]`

---

## Rule set per track

### Track A — "Pattern Notebook" (Tuesday)

> Concrete technical lesson rooted in code, not biography.

1. **Subject** — a pattern, primitive, or idiom you can show in 1-2 code snippets (e.g., discriminated unions, middleware order, JWT refresh flow).
2. **Anchor** — 1 technology + 1 specific pattern. Not "React intro", not "10 tips".
3. **Structure** — Problem → Naive solution → Better solution → Trade-off.
4. **Proof** — at least 1 runnable code snippet.
5. **Voice** — explanatory, second-person ("when you see X, reach for Y").
6. **Closing** — "When to NOT use this" or a known trade-off.
7. **Length** — 800–1500 words.
8. **Forbidden** — "Top 5", "Ultimate guide", listicle, AI-slop summary, anything biographical.
9. **Examples come from** — generic shapes: "a Node REST API", "a React dashboard", "an Express server". Never named projects or clients.

### Track B — "Engineer's Lens" (Thursday)

> This week's hype → actually try it → balanced verdict.

1. **Source** — a real news item / release from that week.
2. **Trigger** — actually try it: read docs, build a small POC, give it a real task.
3. **Structure** — Hype claim → What I tried → What happened → Verdict.
4. **Verdict** — balanced. Neither pure rage nor pure praise.
5. **Length** — 600–1200 words.
6. **Sources** — ≥ 2: the announcement + real-world usage.
7. **Tone** — skeptical-but-fair. The engineer who reads the docs.
8. **Closing** — "Where this is the right tool" + "Where it's not."
9. **Forbidden** — same as Track A. No "I work at...", no "as a junior I...".

### Universal rules

- **Workflow** — `src/content/blog/{slug}.md` → `git push` → ~90 sec live.
- **Frontmatter** — `title`, `description` (≤140 chars), `pubDate`, `tags` (1–4).
- **Hook** — first sentence < 140 chars. Must be directly copy-paste-able as a LinkedIn hook.
- **AI use** — outline, structure, edit pass: fine. Body voice must be mine.
- **LinkedIn distribution** — post 2–3 paragraph excerpt + put the full link (`yldzozgur.com/writing/...`) in the **first comment**, not the post body.
- **Tags vocabulary** — keep tight: `typescript`, `react`, `node`, `code-review`, `tooling`, `ai`, `databases`, `testing`, `postgres`, `mongodb`. Reuse, don't invent. Avoid `career` (biographical signal).

---

## Calendar

### Week 1 — May 19 + 21

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue May 19 | A | `static-types-across-stacks` | Static typing across stacks — what changes when JavaScript types replace Java generics | Compare how each language models the same domain. Use generic shapes: a User record, a payment intent. |
| Thu May 21 | B | `cursor-vs-claude-code-pr` | Cursor vs Claude Code — same PR, two tools, side by side | Fresh small repo. Apply the same refactor with each. Report token use, friction, output diff. |

### Week 2 — May 26 + 28

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue May 26 | A | `discriminated-unions-typescript` | Discriminated unions in TypeScript — when `null` isn't enough | Use a generic API error type. Show `kind: 'validation' \| 'not-found' \| 'unauthorized'` handler. |
| Thu May 28 | B | `ai-and-junior-roles` | AI and junior roles — separating hype from data | Pull hiring data + framework reports. No "what I see at work." |

### Week 3 — Jun 2 + 4

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 2 | A | `splitting-large-prs` | Splitting large PRs — when one becomes five | Decision principle + small refactor example. No "my first PR." |
| Thu Jun 4 | B | `[SWAP-framework-release]` | `[SWAP]` — building a small thing to test the headlines | Pick the week's framework / library release. |

### Week 4 — Jun 9 + 11

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 9 | A | `createslice-vs-rtk-query` | `createSlice` vs RTK Query — when to use which | Decision rubric. A todo list as the running example. |
| Thu Jun 11 | B | `[SWAP-ai-release]-vs-marketing` | `[SWAP]` vs the marketing — three things the demo skipped | Build with the release, list real friction. |

### Week 5 — Jun 16 + 18

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 16 | A | `express-middleware-order` | Express middleware order — the bugs you only see in production | Generic middleware chain: parse → auth → rate-limit → log → handler → error. |
| Thu Jun 18 | B | `bun-vs-node-wins` | Bun vs Node — performance, ecosystem, and where each wins | Run a tiny REST API on both, measure cold start + ecosystem gaps. |

### Week 6 — Jun 23 + 25

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 23 | A | `openapi-snapshot-testing` | Snapshot-testing your OpenAPI spec — catching API drift before deploy | Build the example on a fresh tiny Express + zod-to-openapi. |
| Thu Jun 25 | B | `[SWAP-ai-agent]-real-ticket` | `[SWAP]` autonomous agent — what it does with a real ticket | Pick the week's agent. Give it an issue from a public OSS repo or a generated spec. |

### Week 7 — Jun 30 + Jul 2

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 30 | A | `jwt-refresh-token-ux` | JWT refresh tokens — the silent-refresh UX trade-off | Two patterns: silent refresh vs explicit re-login. Code + sequence diagram. |
| Thu Jul 2 | B | `vibe-coding-or-burnout` | "Vibe coding" — engineering practice or productivity theatre? | Look at what's measurable: throughput, defects, test pass rates. |

### Week 8 — Jul 7 + 9

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jul 7 | A | `cypress-vs-unit-where` | Cypress E2E vs unit tests — what each catches the other can't | Side-by-side: a login flow with three layers of coverage. |
| Thu Jul 9 | B | `typescript-quarter-recap` | Where TypeScript is at the end of the quarter — shipped, deprecated, on the horizon | Survey of TS releases + ecosystem updates over the period. Replaces the personal "did writing get me interviews?" post. |

---

## How to use this doc

1. **Sunday before each week** — open this doc, look at the two slots, fill in `[SWAP]` if needed.
2. **Monday morning** — draft Tuesday's Track A post. Pick the pattern, write the problem, build outward.
3. **Tuesday 10:00 CT** — publish Track A. Push to repo. Wait for Cloudflare deploy. Share to LinkedIn (excerpt + link in first comment).
4. **Wednesday morning** — pick / try the Track B subject. The "actually try it" step is what makes this category work.
5. **Thursday 10:00 CT** — publish Track B. Same LinkedIn pattern.

## Weekly time budget

| Block | Time |
|---|---|
| Pick / scope topic | 30 min |
| Draft (Track A) | 2–3 hrs |
| Draft (Track B) | 1.5–2.5 hrs |
| Edit + read aloud pass | 30 min × 2 |
| LinkedIn post copy | 15 min × 2 |
| **Total / week** | **5–7 hrs** |

If a week's budget runs over, **drop the Thursday post**, don't drop the Tuesday post. Tuesdays are the evergreen anchor; Thursdays can move ±1 day.

## Sustainability rules

- **Miss > skip**: if you can't ship Thursday on Thursday, ship it Friday. Don't disappear.
- **Streak > perfection**: better to publish 8 mediocre posts than 4 great posts and 4 ghosts.
- **First three weeks decide everything**: if you publish all 6 posts in W1–W3, momentum compounds.
- **Re-evaluate after W4**: if cadence is too much, drop to 1 post/week (alternating tracks). Don't drop quality.
