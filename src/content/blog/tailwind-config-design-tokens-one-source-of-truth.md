---
title: "tailwind.config design tokens: one source of truth for colors and spacing."
description: "How to extend Tailwind's config with custom design tokens so your brand colors, spacing scale, and typography are defined once and used everywhere."
pubDate: 2025-01-23
tags: ["Tailwind", "CSS"]
draft: false
---

## Why design tokens matter

Without a shared reference, colors and spacing drift. One developer writes `#2563EB`, another writes `#1D4ED8`, both thinking they're using the brand blue. One component has `padding: 12px`, another has `padding: 14px`. The design slowly becomes inconsistent.

Design tokens are named values that represent design decisions. Instead of a hex code, you use `primary`. Instead of a pixel value, you use `space-3`. The token defines the value once; everything references the token.

In Tailwind, `tailwind.config.js` is where your design tokens live.

## Extending vs replacing

Tailwind's default theme has hundreds of colors, spacing values, and type sizes. You can either add to them with `theme.extend` or replace them entirely with `theme`.

```javascript
// tailwind.config.js

module.exports = {
  theme: {
    // Replaces ALL colors -- default palette gone
    colors: {
      primary: '#2563EB',
      danger: '#DC2626',
    },
  },
};

// vs.

module.exports = {
  theme: {
    extend: {
      // Adds to existing colors -- default palette still available
      colors: {
        primary: '#2563EB',
        danger: '#DC2626',
      },
    },
  },
};
```

For most projects, `extend` is the right choice. You keep Tailwind's utility colors (`red-500`, `gray-200`) while adding your brand-specific tokens.

## A realistic color token setup

Brand colors usually have multiple shades for hover states, backgrounds, and borders:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          900: '#1E3A8A',
        },
        neutral: {
          50: '#F9FAFB',
          200: '#E5E7EB',
          500: '#6B7280',
          900: '#111827',
        },
        danger: '#DC2626',
        success: '#16A34A',
      },
    },
  },
};
```

Now `bg-brand-600`, `text-brand-50`, `border-brand-700` all work as Tailwind utilities. The hex codes live in one place.

## Custom spacing scale

If your design uses a specific set of spacing values, define them:

```javascript
module.exports = {
  theme: {
    extend: {
      spacing: {
        '18': '4.5rem',    // 72px
        '88': '22rem',     // 352px
        '128': '32rem',    // 512px
        'sidebar': '280px', // named value
      },
    },
  },
};
```

`w-sidebar`, `pl-18`, `h-128` become valid classes. Named values like `sidebar` communicate intent better than magic numbers.

## Typography tokens

Custom font families, sizes, and weights:

```javascript
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Cal Sans', 'Inter', 'sans-serif'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'display-lg': ['3.75rem', { lineHeight: '1', letterSpacing: '-0.02em' }],
      },
    },
  },
};
```

The array syntax for `fontSize` lets you specify line height alongside the font size, keeping related values together.

## Using CSS variables for runtime theming

If you need to change tokens at runtime (for multiple brand themes), CSS variables work well as the underlying value:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        secondary: 'rgb(var(--color-secondary) / <alpha-value>)',
      },
    },
  },
};
```

```css
/* globals.css */
:root {
  --color-primary: 37 99 235;  /* blue-600 */
  --color-secondary: 124 58 237; /* violet-600 */
}

.theme-green {
  --color-primary: 22 163 74;  /* green-600 */
}
```

The `/ <alpha-value>` syntax lets Tailwind's opacity modifiers work with your custom colors -- `bg-primary/50` for 50% opacity.

## Referencing tokens in components

With the config in place, components use semantic names:

```html
<button class="bg-brand-600 hover:bg-brand-700 text-white focus:ring-brand-500">
  Submit
</button>

<p class="text-neutral-500 font-sans text-base">
  Supporting text
</p>
```

Changing the brand color means changing one line in the config. Every component using `brand-600` updates automatically at build time.
