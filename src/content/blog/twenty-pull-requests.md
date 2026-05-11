---
title: "What 20 pull requests on a real codebase taught me that the bootcamp didn't"
description: "The gap between finishing a bootcamp and contributing to production code is not about syntax. It's about everything else."
pubDate: 2026-05-10
tags: ["career", "typescript", "code-review"]
draft: true
---

When I finished the Clarusway bootcamp in October 2025, I could build a CRUD app end-to-end. JWT auth, Mongoose models, a React dashboard with Redux Toolkit, Swagger docs, deploy to Vercel — the whole stack. I had three live APIs and a full MERN dashboard to show for it.

Two weeks later I opened my first pull request at Ameza Solutions. It was forty lines of TypeScript, and it took me three days.

This post is about the gap between those two states — what shipping real code in a real team actually requires, beyond writing code that works on your machine.

## 1. Reading code is harder than writing it

In the bootcamp, every project starts with an empty folder. You design the schema, name the files, decide the conventions. By the time you're done, you understand it because you built it.

A real codebase already has thousands of decisions baked in. The first thing I had to do at Ameza was spend a week just _reading_ — following imports, tracing how a request flowed from the React form through the validation utilities through the typed DTO through the controller through the service through the database. There was no bug to fix yet. I was just trying to load the map into my head.

The lesson: code reading is a separate skill from code writing, and bootcamps don't teach it because every bootcamp project is too small to need it.

## 2. The PR is the deliverable, not the code

A working feature on my laptop is not the deliverable. A reviewable pull request is.

That means:

- **Small.** My first PR was 40 lines because I broke a 200-line task into five. Each one stands alone.
- **Described.** Every PR needs a description that explains _why_, not _what_. The diff already shows what.
- **Tested.** Not necessarily unit tests — but at minimum, screenshots, a video of the flow working, or steps for the reviewer to verify.
- **Self-reviewed.** Before requesting a review, I read my own diff in the GitHub UI. I catch half my own mistakes that way.

The first time my tech lead said "can you split this PR" I felt like I had done something wrong. I hadn't — I had just done something the bootcamp had never asked me to do.

## 3. Conventions matter more than correctness

There were three ways to handle errors in the codebase when I joined. The "correct" one — the one matching the existing pattern — wasn't the most elegant. It was the one everyone else was already using.

When you're alone, the best code is the code you understand. When you're on a team, the best code is the code _everyone_ understands. That means following the existing pattern even when you'd write it differently from scratch.

This was hard for me because the bootcamp taught me to have opinions. The job is teaching me when to hold them.

## 4. The review is the feature

I used to think a code review was the price of admission — the thing I had to suffer through to get my code merged. Now I think it's the most valuable part of the workflow.

Every review on my PRs has taught me something I would never have discovered on my own: an existing utility I didn't know about, a TypeScript pattern I hadn't seen, a domain decision I had quietly violated. The first comment on my first PR was: _"We use the `discriminatedUnion` pattern for these — see `src/errors/codes.ts`."_ I didn't even know discriminated unions existed.

The bootcamp had me reviewing classmates' code, but it wasn't the same. Classmates don't know the codebase either. A senior reviewer does, and every comment is a free lesson from someone who has already made the mistake you're about to make.

## 5. What I'd tell myself six months ago

If I could go back to October 2025 — the version of me who had just finished the bootcamp and was applying to jobs — I'd tell him three things:

1. **Find a real codebase to read.** Open source, volunteer, internship, doesn't matter. The bootcamp portfolio is necessary but not sufficient. Recruiters can't tell whether your code came from a tutorial or your own head. A merged PR on a real repo is unambiguous.

2. **Practice splitting work.** Take one of your bootcamp projects and pretend you have to deliver it in five PRs of 50 lines each. Figure out how. This is the skill that makes you employable on day one.

3. **Stop optimizing for cleverness.** Nobody on a real team is impressed by a one-line solution to a three-line problem. They're impressed by code they can review in two minutes and merge with confidence.

---

I'm still at the beginning of this. Twenty merged PRs is not a lot. But every one has taught me something the bootcamp couldn't, and I'm writing here partly to keep track of those lessons — and partly because I think the next person walking out of a bootcamp deserves to know what's actually waiting for them.
