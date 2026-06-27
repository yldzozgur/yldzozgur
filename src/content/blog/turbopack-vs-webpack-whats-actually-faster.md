---
title: "Turbopack vs webpack: what's actually faster."
description: "What Turbopack is, how it differs from webpack architecturally, what the benchmarks measure, and where it stands today."
pubDate: 2026-03-16
tags: ["Architecture"]
draft: false
---

Turbopack is a JavaScript/TypeScript bundler written in Rust, built by the Vercel team. It's positioned as the successor to webpack and ships as the default bundler in Next.js 13+. The claims are impressive. The benchmarks require some interpretation.

## What's slow about webpack

webpack is a JavaScript process. At its core, it builds a module dependency graph and transforms each module through a pipeline of loaders. The bottlenecks:

- **JavaScript overhead:** each module transformation (TypeScript compilation, CSS processing, JSX transform) runs in a JS process. Fast for small projects, slow for thousands of modules.
- **Single-threaded execution:** webpack can parallelize some work with `thread-loader`, but it's bolt-on, not fundamental.
- **Full rebuilds on change:** webpack's incremental rebuilds with HMR have improved, but invalidating the right parts of a large graph is complex.

Vite solved the development speed problem differently: don't bundle at all during development. Serve ES modules directly with native browser imports, use esbuild (written in Go) for transformations, and only bundle for production. This is fast because the browser handles module loading and only changed modules are re-transformed.

## What Turbopack does differently

Turbopack is built around an incremental computation engine called Turbo. The core idea: every computation is tracked with its inputs and outputs. When an input changes, only computations that depend on that input are re-run. This is similar to how build systems like Bazel or Buck work, but applied to the module graph at the function level.

In practice: change a component file, and only the minimal set of modules that depend on it are re-bundled. The work scales with what changed, not with the size of the project.

The Rust implementation eliminates the JavaScript runtime overhead per module transformation.

## What the benchmarks show

The headline benchmark from the Turbopack announcement: "10x faster than webpack, 700x faster than webpack in large projects." These numbers measured HMR (hot module replacement) update time on a synthetic project with 30,000 components.

The caveats:
- The comparison was against a Webpack 4 configuration without optimizations, not against a well-tuned Webpack 5 setup with persistent caching
- Vite wasn't included in initial benchmarks
- Synthetic 30,000-component projects don't match real-world app structures

Independent benchmarks (from the Vite team and others) showed Vite's dev server remaining competitive with Turbopack for typical project sizes, with Turbopack pulling ahead on very large monorepos.

## The current state

As of 2026:

**Next.js dev server:** Turbopack is stable and the default for `next dev`. Real-world feedback from large Next.js apps reports meaningful cold start and HMR improvements over Webpack.

**Production builds:** Turbopack's production bundler (`next build --turbo`) reached stability in Next.js 15. It's now the recommended path for new Next.js projects.

**Outside Next.js:** Turbopack is designed to be framework-agnostic but is primarily used through Next.js. The standalone API is less mature.

## Comparison with Vite

For projects not using Next.js, Vite remains the dominant choice for its development experience. Vite's dev server (native ES modules + esbuild) is fast enough for the vast majority of projects and has a mature plugin ecosystem.

Turbopack's advantage is in projects where bundling during development is necessary (Next.js's server rendering architecture requires it) and in very large projects where Vite's "serve everything unbundled" approach gets slow due to large numbers of small requests.

For a greenfield Next.js project: use Turbopack (it's the default). For a Vite-based project: stay with Vite unless you're hitting concrete performance problems. For a webpack project not on Next.js: consider Vite as the migration target before Turbopack.
