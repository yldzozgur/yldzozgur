---
title: "The browser rendering pipeline: DOM, CSSOM, layout, paint, composite."
description: "How the browser turns HTML and CSS into pixels on screen, and what that means for writing performant web code."
pubDate: 2026-01-19
tags: ["Architecture"]
draft: false
---

Every time you change a DOM element or CSS property, you're triggering some portion of the browser's rendering pipeline. Understanding what triggers what helps you write code that doesn't make the browser do unnecessary work.

## Step 1: Parsing

The browser downloads HTML and parses it into the **DOM** (Document Object Model) -- a tree of nodes. Simultaneously, it encounters `<link>` and `<style>` tags and parses CSS into the **CSSOM** (CSS Object Model) -- a separate tree of style rules.

HTML parsing is incremental and tolerant of errors. CSS parsing is not incremental -- the browser won't render until it has enough CSS to construct the CSSOM, because styles can affect layout. This is why render-blocking CSS matters.

## Step 2: Style calculation

The browser combines the DOM and CSSOM into a **render tree** -- the DOM nodes that will actually be displayed (excluding `display: none` elements and pseudo-content like `::before`), each annotated with their computed styles.

This step is called **recalculate style**. It happens whenever:
- CSS rules change
- Classes are added or removed
- Inline styles are modified
- The DOM structure changes

The cost scales with the number of elements and the complexity of CSS selectors.

## Step 3: Layout (Reflow)

With the render tree, the browser calculates the exact position and size of every element. This is **layout** (sometimes called reflow). It answers: where does this element go, how wide is it, how tall?

Layout is expensive. It's also cascading -- changing the size of a parent element can force re-layout of all its children. Changing anything that affects geometry (width, height, margin, padding, top, left, font-size) triggers layout.

Some things that trigger layout:

```javascript
// Reading layout properties triggers layout if the DOM is "dirty"
const width = element.offsetWidth;
const rect = element.getBoundingClientRect();

// Writing properties that affect geometry
element.style.width = '200px';
```

**Forced synchronous layout** (also called layout thrashing) is reading a layout property immediately after writing one:

```javascript
// Bad: read/write/read/write in a loop
for (const el of elements) {
  el.style.width = container.offsetWidth + 'px'; // read, then write
}

// Good: batch reads before writes
const w = container.offsetWidth;
for (const el of elements) {
  el.style.width = w + 'px';
}
```

The first loop forces the browser to re-run layout on every iteration. The second reads once and writes in a batch.

## Step 4: Paint

Layout produces a list of boxes with positions. **Paint** turns those boxes into pixels: fills colors, draws text, renders borders and shadows. This happens on CPU, layer by layer.

Paint is triggered by visual changes that don't affect geometry: `color`, `background-color`, `box-shadow`, `border-radius`, `outline`. It's cheaper than layout because positions don't change, but it's still not free.

You can see which elements are repainting in Chrome DevTools by enabling "Paint flashing" in the Rendering panel.

## Step 5: Composite

Modern browsers split the page into **layers** and composite them on the GPU. This is the final step -- assembling the painted layers into the final frame.

Some CSS properties trigger layer promotion, which means changes to those properties skip layout and paint entirely and only require compositing on the GPU:

- `transform`
- `opacity`
- `filter`
- `will-change`

This is why CSS animations on `transform` and `opacity` are smooth while animations on `top`/`left` or `width` are not. The former only requires compositing; the latter re-triggers layout.

```css
/* Triggers layout + paint on every frame */
.bad-animation {
  transition: left 300ms;
}

/* Only triggers composite -- smooth at 60fps */
.good-animation {
  transition: transform 300ms;
}
```

## Practical implications

**Minimize layout triggers.** Batch DOM reads before writes. Use `requestAnimationFrame` to defer DOM mutations to the next frame. Use `ResizeObserver` instead of polling `offsetWidth`.

**Promote composited layers intentionally.** Don't add `will-change: transform` to everything -- it consumes memory. Add it to elements you know will animate.

**Profile before optimizing.** Open Chrome DevTools, record a Performance trace, and look for long "Layout" and "Paint" bars in the flame chart. Optimize where you see actual time being spent, not where you guess.

**CSS containment.** The `contain` property tells the browser that changes inside an element won't affect anything outside it, allowing it to skip parts of the pipeline for the rest of the page. More on that in the CSS containment post.

The rendering pipeline is not magic. It's a sequence of deterministic steps that your code triggers. Once you know which CSS properties and DOM operations trigger which steps, writing performant UI code becomes straightforward.
