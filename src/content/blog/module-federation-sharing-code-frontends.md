---
title: "Module federation: sharing code between independently deployed frontends."
description: "How Webpack Module Federation works, when micro-frontends make sense, and the pitfalls of sharing code across deployment boundaries."
pubDate: 2026-02-23
tags: ["Architecture"]
draft: false
---

Module Federation is a Webpack 5 feature that lets one JavaScript application load code from another at runtime. It's the technical mechanism behind micro-frontend architectures, but it has a sharper set of tradeoffs than the name suggests.

## The problem it solves

You have a large frontend application split across multiple teams. Each team wants to deploy independently. Without Module Federation, you either:

1. Build everything into one bundle (no independent deploys)
2. Use iframes (works but isolated -- no shared state, navigation, or UI consistency)
3. Publish shared components as npm packages (independent deploys, but shared library updates require all consumers to upgrade and redeploy)

Module Federation enables option 4: each team's app is deployed separately, but components and utilities can be shared at runtime without republishing npm packages.

## How it works

In a Module Federation setup, you have:

- **Remotes:** applications that expose modules for others to consume
- **Hosts:** applications that consume modules from remotes

The remote's webpack config declares what it exposes:

```javascript
// webpack.config.js -- the "checkout" team's app
const { ModuleFederationPlugin } = require('webpack').container;

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'checkout',
      filename: 'remoteEntry.js',
      exposes: {
        './CheckoutFlow': './src/CheckoutFlow',
        './CartSummary': './src/CartSummary',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
      },
    }),
  ],
};
```

The host consumes it:

```javascript
// webpack.config.js -- the "shell" app
new ModuleFederationPlugin({
  name: 'shell',
  remotes: {
    checkout: 'checkout@https://checkout.example.com/remoteEntry.js',
  },
  shared: {
    react: { singleton: true, requiredVersion: '^18.0.0' },
    'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
  },
})
```

```tsx
// In the shell app
const CheckoutFlow = React.lazy(() => import('checkout/CheckoutFlow'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <CheckoutFlow />
    </Suspense>
  );
}
```

The shell fetches `remoteEntry.js` from the checkout app at runtime. If the checkout team deploys a new version, the shell picks it up on the next page load without a redeploy.

## The `shared` config is critical

The `shared` configuration prevents multiple copies of React from loading. If the host and remote each bundle their own React, you get two React instances, which causes hooks to fail and context to not propagate.

`singleton: true` means only one copy of React will be loaded, regardless of which app loads first. If version requirements conflict (host wants React 18.2, remote wants 18.0), you get a console warning and the higher version is used.

## Rspack and Vite

Module Federation isn't Webpack-only anymore. Both Rspack (a Rust-based Webpack-compatible bundler) and Vite support Module Federation through the `@module-federation/vite` plugin, with roughly the same API.

## The real costs

Module Federation enables independent deploys, but it doesn't make that free:

**Runtime loading failures.** The remote is a runtime HTTP dependency. If the checkout team's deployment breaks their `remoteEntry.js`, the shell app breaks at runtime, not at build time. You need error boundaries and graceful fallbacks:

```tsx
function CheckoutPage() {
  return (
    <ErrorBoundary fallback={<CheckoutUnavailable />}>
      <Suspense fallback={<Loading />}>
        <RemoteCheckout />
      </Suspense>
    </ErrorBoundary>
  );
}
```

**Version coordination.** The `shared` config creates an implicit contract. If the checkout team upgrades to React 19 and the shell team hasn't, `singleton: true` will use whichever loads first, potentially causing incompatibilities.

**Debugging complexity.** Stack traces and source maps span deployment boundaries. Errors in the remote show up in the host, and the connection isn't obvious.

**When is it worth it?**

Module Federation makes sense when teams are genuinely independent, have separate deployment pipelines, and the coordination cost of a shared bundle outweighs the operational complexity of federation. For most applications with a single frontend team, it adds complexity with no benefit.
