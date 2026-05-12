# Content calendar — 2 months / 16 posts

**Window:** 2026-05-19 → 2026-07-09 (8 weeks, 2 posts/week)
**Cadence:** Tuesday + Thursday, 10:00 Central
**Total:** 16 posts across two tracks

---

## Rule set

### Track A — "Stack Notebook" (Tuesday)

> Concrete lesson from a technology I actually use.

1. **Source** — a real moment: an Ameza PR, a bug, a code review comment, a refactor. Not from the top of my head; from work.
2. **Anchor** — 1 technology + 1 specific pattern. Example: "TypeScript discriminated unions", "Express middleware ordering". Not "React intro".
3. **Structure** — Problem → What I tried → What I learned → Trade-off.
4. **Proof** — at least 1 code snippet (real or recreatable).
5. **Voice** — junior who has done this. Not teacher.
6. **Verifiable detail** — specific PR, number, behavior. E.g. "my 40-line PR took 3 days because…"
7. **Closing** — "What I'd do differently" or a trade-off to be aware of.
8. **Length** — 800–1500 words.
9. **Forbidden** — "Top 5", "Ultimate guide", generic intro, listicle, AI-slop.

### Track B — "Engineer's Lens" (Thursday)

> This week's hype → I actually tried it → balanced verdict.

1. **Source** — a real news item / release / hype from that week.
2. **Trigger** — before writing, actually try it: read the docs, build a small POC, give it a real task.
3. **Structure** — Hype claim → What I tried → What actually happened → My take.
4. **Verdict** — balanced. Neither pure rage nor pure praise. Where the hype is right, where it's overblown.
5. **Length** — 600–1200 words (shorter, opinion-driven).
6. **Sources** — at least 2: the original announcement + real-world usage.
7. **Tone** — skeptical-but-fair. The engineer who reads the actual docs.
8. **Closing** — "Would I use this at Ameza? Why / why not?"
9. **Forbidden** — AI-slop summary, marketing recap, pure rage, headline-only takes.

### Universal rules

- **Workflow** — `src/content/blog/{slug}.md` → `git push` → ~90 sec live.
- **Frontmatter** — `title`, `description` (≤140 chars), `pubDate`, `tags` (1–4).
- **Hook** — first sentence < 140 chars. Must be directly copy-paste-able as a LinkedIn hook.
- **AI use** — outline, structure, edit pass: fine. Body voice must be mine.
- **LinkedIn distribution** — post 2–3 paragraph excerpt + put the full link (`yldzozgur.com/writing/...`) in the **first comment**, not the post body. Algorithm penalty for external links in body.
- **Tags vocabulary** — keep tight: `typescript`, `react`, `node`, `career`, `code-review`, `tooling`, `ai`, `databases`, `testing`, `postgres`, `mongodb`. Reuse, don't invent.

---

## Calendar

### Week 1 — May 19 + 21

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue May 19 | A | `reading-multi-tenant-codebase` | Reading a multi-tenant codebase for the first time | First-contact map of Ameza's structure. The mental model I drew. |
| Thu May 21 | B | `cursor-vs-claude-code` | Cursor vs Claude Code in a real PR — actual differences | `[SWAP]` if a different AI tool dominates that week. |

### Week 2 — May 26 + 28

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue May 26 | A | `discriminated-unions-typescript` | Discriminated unions: the TS pattern I missed in bootcamp | The error-code refactor that clicked. Real before/after. |
| Thu May 28 | B | `ai-replacing-juniors-panic` | The "AI will replace juniors" panic — what I actually see at work | Use real anecdotes from Ameza code review. |

### Week 3 — Jun 2 + 4

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 2 | A | `splitting-large-pr` | Why I split my first 200-line PR into five | The review feedback that taught me atomic PRs. |
| Thu Jun 4 | B | `[SWAP-framework-release]` | `[SWAP]` — building a real thing to see if it lives up | Pick the week's framework / library release. |

### Week 4 — Jun 9 + 11

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 9 | A | `redux-toolkit-vs-rtk-query` | Redux Toolkit `createSlice` vs RTK Query — when I pick which | Decision rubric from Stock Mgmt app. |
| Thu Jun 11 | B | `[SWAP-ai-release]-vs-demo` | `[SWAP]` vs the marketing — three things the demo skipped | Build something with the new release, list real friction. |

### Week 5 — Jun 16 + 18

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 16 | A | `express-middleware-order` | Express middleware order — what catches you in production | Real middleware suite from Stock Mgmt API: auth → errors → logging → permissions → queries. |
| Thu Jun 18 | B | `bun-vs-node-production` | Bun vs Node in production — would I ship it at Ameza? | Run a real Ameza-like service on both, measure, decide. |

### Week 6 — Jun 23 + 25

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 23 | A | `swagger-snapshot-sync` | Swagger snapshot sync — the trick that catches API drift before deploy | Real workflow from Ameza. |
| Thu Jun 25 | B | `[SWAP-ai-agent]-real-ticket` | `[SWAP]` — I gave it a real Ameza ticket. Here's what it produced. | Pick the week's hyped autonomous agent. |

### Week 7 — Jun 30 + Jul 2

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jun 30 | A | `jwt-refresh-token-ux` | JWT refresh tokens — the UX trade-off no tutorial mentions | The silent-refresh implementation from Stock Mgmt. |
| Thu Jul 2 | B | `vibe-coding-reality` | "Vibe coding" — real engineering practice or burnout speedrun? | Honest take after using AI-first workflows for 6 months. |

### Week 8 — Jul 7 + 9

| Day | Track | Slug | Title | Notes |
|---|---|---|---|---|
| Tue Jul 7 | A | `cypress-e2e-worth-it` | Cypress E2E — what's worth testing vs. unit tests | Pizza API + Stock Mgmt E2E experience. |
| Thu Jul 9 | B | `two-months-writing-retro` | Two months of writing weekly — did it help me get interviews? | Meta-post. Honest metrics: traffic, interviews, LinkedIn follows. Closes the loop. |

---

## How to use this doc

1. **Sunday before each week** — open this doc, look at the two slots, fill in `[SWAP]` if needed with that week's actual hot topic.
2. **Monday morning** — draft Tuesday's Track A post. Pick a real Ameza moment, write the problem statement, then build outward.
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
- **Streak > perfection**: better to publish 8 mediocre posts you wrote than 4 great posts and 4 ghosts.
- **First three weeks decide everything**: if you publish all 6 posts in W1–W3, momentum compounds. If you miss two, the calendar dies.
- **Re-evaluate after W4**: if the cadence is too much, drop to 1 post/week (alternating tracks). Don't drop quality.
