---
title: "Font loading: the FOUT/FOIT problem and the CSS that fixes it."
description: "Why web fonts cause layout shift and invisible text, and how font-display, preload, and size-adjust solve it."
pubDate: 2026-03-02
tags: ["Architecture"]
draft: false
---

Web fonts improve typography but they introduce a race condition: the browser needs to render text before the font has downloaded. How it handles that race determines whether users see a flash of unstyled text (FOUT) or invisible text (FOIT) before the font arrives.

## The two failure modes

**FOIT (Flash of Invisible Text):** The browser hides text until the custom font loads. Users see a blank page for however long the font takes. The default behavior in most browsers for a font that takes more than 3 seconds is to fall back to the system font, but during those 3 seconds, text is invisible.

**FOUT (Flash of Unstyled Text):** Text renders immediately with the fallback font, then snaps to the custom font when it loads. This looks like a flash because the fallback and custom font have different sizes and metrics, causing text to reflow.

Both are bad, but they're not equally bad. FOIT actively hides content from users. FOUT at least shows something. The goal is to minimize both.

## font-display

The `font-display` descriptor in `@font-face` controls this behavior:

```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter.woff2') format('woff2');
  font-display: swap;
}
```

The five values:

- **`auto`**: browser default. Usually FOIT.
- **`block`**: FOIT for up to 3 seconds, then FOUT. Worst of both worlds.
- **`swap`**: FOUT immediately. Text shows right away, swaps when font loads. Good for body text.
- **`fallback`**: short FOIT (100ms), then FOUT. If font loads within 3 seconds, swap; otherwise stick with fallback.
- **`optional`**: very short FOIT, then fallback. If font isn't cached, don't even try to swap. Good for non-critical decorative fonts.

For body text where legibility matters most, `font-display: swap` is the right default. Users see text immediately; the swap happens quickly as fonts are small files.

## Preloading critical fonts

`font-display: swap` fixes FOIT but doesn't make fonts load faster. To reduce the FOUT window, preload the fonts used above the fold:

```html
<link
  rel="preload"
  href="/fonts/inter-variable.woff2"
  as="font"
  type="font/woff2"
  crossorigin
/>
```

The `crossorigin` attribute is required even for same-origin fonts because fonts are fetched with CORS. Without it, the browser fetches the font twice: once for the preload (without CORS) and once when the CSS is parsed (with CORS).

Preload only fonts that are actually used in the visible viewport. Preloading 10 fonts defeats the purpose.

## Size-adjust: eliminating layout shift

Even with `font-display: swap`, the fallback-to-custom font swap causes Cumulative Layout Shift (CLS) because fallback fonts have different metrics. `size-adjust`, `ascent-override`, `descent-override`, and `line-gap-override` let you tune the fallback font to match the custom font's dimensions:

```css
@font-face {
  font-family: 'Inter-fallback';
  src: local('Arial');
  size-adjust: 107%;
  ascent-override: 90%;
  descent-override: 22%;
  line-gap-override: 0%;
}

body {
  font-family: 'Inter', 'Inter-fallback', sans-serif;
}
```

When `Inter` loads, it swaps with `Inter-fallback`. Because the adjusted fallback has the same visual dimensions as Inter, text doesn't reflow and CLS stays near zero.

Finding the right values: the `fontaine` package can auto-generate these overrides, or you can use Chrome DevTools' Font Editor or websites like `screenspan.com/font-override-css`.

## Google Fonts and self-hosting

Google Fonts adds an extra DNS lookup and connection per domain. Self-hosting removes that:

```bash
# Download fonts and generate CSS with @fontsource
npm install @fontsource-variable/inter
```

```typescript
// In your app entry point
import '@fontsource-variable/inter';
```

`@fontsource` packages self-host Google Fonts, serving them from your own CDN. Variable fonts (with a weight range rather than separate files per weight) reduce the number of font files from 6 (for 6 weights) to 1.

## The checklist

1. Use WOFF2 (best compression, supported by all modern browsers)
2. `font-display: swap` for text fonts
3. `<link rel="preload">` for fonts in the LCP element
4. `size-adjust` on the fallback font to eliminate CLS
5. Self-host rather than using Google Fonts if latency is a concern
6. Use variable fonts to reduce file count

Getting fonts right is one of the higher-leverage CLS improvements because it's purely a configuration problem -- no architectural changes required.
