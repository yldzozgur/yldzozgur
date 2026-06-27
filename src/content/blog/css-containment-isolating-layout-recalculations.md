---
title: "CSS containment: the property that isolates layout recalculations."
description: "How the CSS contain property works, what containment types exist, and how content-visibility accelerates rendering of off-screen content."
pubDate: 2026-03-05
tags: ["Architecture"]
draft: false
---

When you change a DOM element's size or content, the browser potentially needs to recalculate layout for the entire page -- because any element could affect any other. CSS containment lets you tell the browser that a subtree is isolated, so changes inside it can't affect anything outside.

## The contain property

`contain` accepts one or more containment types:

```css
.widget {
  contain: layout style paint;
}
```

**`layout`**: children of this element don't affect the layout of elements outside it. If something inside the widget changes size, the browser only needs to reflow the widget's subtree, not the entire page.

**`style`**: CSS counters and quotes inside the element are scoped to it. Prevents style effects from leaking out.

**`paint`**: the element's content is clipped to its border box. Content that overflows isn't rendered. This allows the browser to skip painting elements that are entirely outside the viewport.

**`size`**: the element's size is independent of its children. You must provide an explicit size. With size containment, the browser doesn't need to look inside the element to compute its dimensions.

**`inline-size`**: size containment in the inline direction only (width in horizontal writing modes). Useful for responsive components without full size containment.

Shorthand values:

```css
contain: content;  /* layout + style + paint */
contain: strict;   /* layout + style + paint + size */
```

## When containment helps

**Virtualized lists.** Even when items are off-screen, their DOM nodes can affect layout if they don't have containment. Adding `contain: strict` with explicit dimensions to list items tells the browser to skip them entirely for layout and paint calculations.

**Widgets and components.** A dashboard with 20 independent widgets: updating one widget's data shouldn't force the browser to recalculate layout for the other 19. `contain: layout` on each widget prevents this.

**Dynamic content.** Elements that animate or update frequently benefit from `contain: layout paint` to scope the rendering work.

```css
.dashboard-widget {
  contain: layout style paint;
  /* Changes inside here are isolated */
}

.list-item {
  contain: strict;
  height: 60px; /* Required for size containment */
}
```

## content-visibility

`content-visibility: auto` is a higher-level optimization built on containment. It tells the browser to skip rendering work (layout and paint) for elements outside the viewport, and to do the work lazily as they scroll into view.

```css
.article-section {
  content-visibility: auto;
  contain-intrinsic-size: 0 500px; /* estimated size when not rendered */
}
```

`contain-intrinsic-size` provides the dimensions to use as a placeholder while the element isn't rendered. Without it, the element would have zero height when off-screen, causing the page height to change as you scroll (which causes janky scrolling).

The browser applies `contain: size layout style paint` automatically to elements with `content-visibility: auto`. When an element scrolls into the viewport, rendering work happens. When it scrolls out, that work is discarded.

**The impact on initial load:**

For pages with long content (news articles, product listings, documentation), `content-visibility: auto` can dramatically reduce initial render time. The browser renders the visible viewport and skips everything below the fold. Chrome has reported 7x rendering time improvements on content-heavy pages.

```css
/* Apply to major page sections */
main > section {
  content-visibility: auto;
  contain-intrinsic-size: 0 400px;
}
```

## Measuring containment benefits

Measure in Chrome DevTools' Performance panel. Record a page load or a user interaction, then look at "Recalculate Style" and "Layout" events in the main thread. Before adding containment, these events may touch hundreds or thousands of nodes. After, they should be scoped to the contained element's subtree.

`content-visibility: auto` impact is visible in the initial "Parse HTML" and "Layout" phases. On a page with hundreds of article cards below the fold, the difference between rendering all of them and deferring all of them is measurable in seconds.

## Browser support

`contain` is supported in all modern browsers. `content-visibility` has full support in Chrome and Edge, and is supported in Firefox and Safari. For unsupported browsers, the fallback is simply normal rendering -- containment is purely an optimization hint, not a functional requirement.

Add it to components that update frequently, to independent widgets, and to major page sections. The downside is negligible; the upside is real.
