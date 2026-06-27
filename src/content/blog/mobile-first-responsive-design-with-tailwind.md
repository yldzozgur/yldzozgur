---
title: "Mobile-first responsive design with Tailwind: the breakpoints that matter."
description: "How Tailwind's breakpoint system works, why mobile-first means unprefixed classes apply to small screens, and which breakpoints to actually use."
pubDate: 2025-01-16
tags: ["Tailwind", "CSS", "Responsive Design"]
draft: false
---

## Mobile-first means start small

In Tailwind, every utility class without a breakpoint prefix applies to all screen sizes. Breakpoint prefixes add styles at that size and above. This is mobile-first: you design the small-screen layout first, then layer on changes for larger screens.

```html
<div class="flex flex-col md:flex-row">
  <!-- Stacked on mobile, side by side on md and up -->
</div>
```

`flex-col` applies everywhere. `md:flex-row` overrides it at the `md` breakpoint and larger. If you think desktop-first, this is backwards at first. The mental model is: "what is the default?" rather than "what should I undo on mobile?"

## The default breakpoints

Tailwind ships with five breakpoints:

| Prefix | Min-width |
|--------|-----------|
| `sm`   | 640px     |
| `md`   | 768px     |
| `lg`   | 1024px    |
| `xl`   | 1280px    |
| `2xl`  | 1536px    |

These correspond to the most common device widths. A typical phone is below `sm`. A tablet lands around `md`. A laptop is `lg`. A wide desktop is `xl` or `2xl`.

## The breakpoints that actually matter

In practice, most layouts only need two or three breakpoints. The common pattern:

- **Base (no prefix)**: phone, single-column layout
- **`md`**: tablet, two-column layout starts making sense
- **`lg`**: desktop, full layout with sidebar or three columns

Using all five breakpoints for every component creates unnecessary complexity. Many UI decisions only need one override -- the mobile layout and the "everything larger" layout. Start with just `md` as your single breakpoint and add others only when content requires it.

## Grid layout example

A product grid that is one column on mobile, two on tablet, three on desktop:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div class="...">Product 1</div>
  <div class="...">Product 2</div>
  <div class="...">Product 3</div>
</div>
```

The `gap-6` applies at all sizes -- gaps usually don't need to change. The column count steps up at each breakpoint.

## Typography scaling

Font sizes often need to increase slightly on larger screens:

```html
<h1 class="text-2xl md:text-3xl lg:text-4xl font-bold">
  Page title
</h1>
```

On mobile, `text-2xl` (1.5rem). On tablet, `text-3xl` (1.875rem). On desktop, `text-4xl` (2.25rem). The progression prevents mobile text from looking cramped or desktop text from looking tiny.

## Hiding and showing elements

Some elements only make sense at certain sizes:

```html
<!-- Mobile-only element -->
<div class="md:hidden">
  <MobileMenu />
</div>

<!-- Desktop-only element -->
<div class="hidden md:block">
  <DesktopSidebar />
</div>
```

`hidden` sets `display: none`. `md:block` sets `display: block` at `md` and up. The two together create a display that switches based on breakpoint.

## Spacing and padding adjustments

Padding that works on desktop often feels excessive on mobile:

```html
<section class="px-4 md:px-8 lg:px-16 py-8 md:py-16">
  <!-- Content -->
</section>
```

Small horizontal padding on mobile keeps content from touching the screen edge. Larger padding on desktop creates breathing room. Vertical padding increases on larger screens where there is more visual space to fill.

## Container with max-width

Most layouts need a max-width to prevent content from stretching across a very wide monitor. The built-in `container` class sets `max-width` to the current breakpoint's width and needs `mx-auto` to center it:

```html
<div class="container mx-auto px-4">
  <!-- Content stays readable on wide screens -->
</div>
```

## Custom breakpoints

If the default breakpoints don't match your design, add custom ones in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    screens: {
      'xs': '480px',
      'sm': '640px',
      'md': '768px',
      // ...
    },
  },
};
```

Adding `xs` for very small phones is the most common extension. Most projects don't need more than that.

The discipline mobile-first requires is writing the simplest layout first and only adding complexity for larger screens. Start with one column, no decorative spacing, and minimal font sizes. Everything above that is an enhancement.
