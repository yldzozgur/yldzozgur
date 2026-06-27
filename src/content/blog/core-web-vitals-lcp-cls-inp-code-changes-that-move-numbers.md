---
title: "Core Web Vitals: LCP, CLS, INP and the code changes that move the numbers."
description: "What each Core Web Vital measures, why it matters for user experience, and the specific code changes that improve each metric."
pubDate: 2025-09-18
tags: ["DevOps"]
draft: false
---

Core Web Vitals are three metrics that measure user experience: how fast the main content loads (LCP), how much the page shifts while loading (CLS), and how quickly the page responds to interaction (INP). They affect search ranking and, more importantly, actual user experience. These are the code changes that move the numbers.

## LCP - Largest Contentful Paint

LCP measures when the largest visible element in the viewport has loaded. The threshold: under 2.5 seconds is good, over 4 seconds is poor. The largest element is usually a hero image or the main heading.

**Eliminate render-blocking resources.** Scripts and stylesheets in `<head>` block rendering. Move non-critical scripts to the end of body or mark them `defer`:

```html
<!-- Blocks rendering: bad -->
<script src="/analytics.js"></script>

<!-- Deferred: runs after HTML parse, doesn't block LCP -->
<script src="/analytics.js" defer></script>
```

**Preload the LCP image.** The browser discovers images late in the loading process. A preload hint tells it to fetch the LCP image earlier:

```html
<link rel="preload" as="image" href="/hero.webp" fetchpriority="high">
```

**Use modern image formats.** WebP is 25-35% smaller than JPEG at equivalent quality. AVIF is smaller still.

```jsx
<picture>
  <source srcSet="/hero.avif" type="image/avif" />
  <source srcSet="/hero.webp" type="image/webp" />
  <img src="/hero.jpg" alt="Hero image" />
</picture>
```

**Never lazy-load the LCP image.** `loading="lazy"` defers the image fetch until it is near the viewport. The LCP image is already in the viewport. Lazy-loading it directly harms LCP.

## CLS - Cumulative Layout Shift

CLS measures visual stability - how much elements move after initial render. The threshold: under 0.1 is good. Layout shifts happen when content loads and pushes other content around.

**Always specify image dimensions.** Without dimensions, the browser does not know how much space to reserve. When the image loads, everything shifts.

```jsx
// Bad: no dimensions, causes layout shift
<img src="/product.jpg" alt="Product" />

// Good: reserves space before image loads
<img src="/product.jpg" alt="Product" width={600} height={400} />
```

In CSS, use `aspect-ratio` for responsive images:

```css
img {
  aspect-ratio: 3/2;
  width: 100%;
}
```

**Reserve space for dynamic content.** Ads, embeds, and lazy-loaded components that appear after the initial render push content down. Use a placeholder with known dimensions:

```jsx
function AdSlot() {
  return (
    <div style={{ minHeight: '250px', width: '300px' }}>
      <AdComponent />
    </div>
  );
}
```

**Use `font-display: optional` or preload fonts.** Web fonts that load after text has rendered in a fallback font cause a flash and layout shift:

```css
@font-face {
  font-family: 'MyFont';
  src: url('/fonts/my-font.woff2') format('woff2');
  font-display: swap; /* Shows fallback, swaps when loaded */
}
```

For critical fonts, preload them:

```html
<link rel="preload" as="font" href="/fonts/my-font.woff2" crossorigin>
```

## INP - Interaction to Next Paint

INP replaced FID in 2024. It measures the latency of the slowest interaction during a visit. The threshold: under 200ms is good, over 500ms is poor. Poor INP means the page feels unresponsive to clicks and keyboard input.

**Long tasks on the main thread are the primary cause.** A JavaScript task that takes 300ms blocks the browser from responding to interactions. Break long tasks:

```javascript
// Bad: single 300ms task blocks interaction
function processLargeDataset(items) {
  return items.map(expensiveOperation);
}

// Good: yields to browser between chunks
async function processLargeDataset(items) {
  const results = [];
  for (let i = 0; i < items.length; i += 100) {
    const chunk = items.slice(i, i + 100);
    results.push(...chunk.map(expensiveOperation));
    // Yield to browser every 100 items
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  return results;
}
```

**Defer non-critical work until after interaction.** State updates triggered by user interaction should do the minimum to render the response. Defer analytics, logging, and secondary updates:

```javascript
function handleButtonClick() {
  // Immediate: update UI
  setSubmitted(true);
  
  // Deferred: analytics can wait
  setTimeout(() => {
    analytics.track('button_clicked');
  }, 0);
}
```

**Use React's `useDeferredValue` for expensive renders.** When a search input triggers an expensive filter operation, defer the expensive computation so the input stays responsive:

```jsx
function SearchResults({ query }) {
  const deferredQuery = useDeferredValue(query);
  
  // This expensive computation uses the deferred (potentially stale) query
  // so the input field stays responsive while it computes
  const results = useMemo(() => filterItems(deferredQuery), [deferredQuery]);
  
  return <ResultsList results={results} />;
}
```

Measuring these metrics in production requires the `web-vitals` library reporting to your analytics. Lab scores from Lighthouse are useful for development but do not represent real user experience. Both matter.
