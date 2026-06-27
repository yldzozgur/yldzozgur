---
title: "Image optimization: format, lazy loading, and the 5 minutes that pay off."
description: "The image optimization techniques with the best effort-to-impact ratio, with concrete implementation examples."
pubDate: 2025-09-22
tags: ["DevOps"]
draft: false
---

Images are typically the largest assets on a web page. On an unoptimized page, images often account for 60-80% of total page weight. The optimizations that move the needle the most take under an hour to implement and compound across every page load.

## Format: the highest-leverage change

JPEG and PNG are the default output of most image tools. Both are older formats. WebP provides 25-35% smaller file sizes at equivalent visual quality for most images. AVIF provides 40-50% smaller files, with broader support arriving in 2024-2025.

The browser picks the best format it supports using the `<picture>` element:

```html
<picture>
  <source srcset="/images/photo.avif" type="image/avif">
  <source srcset="/images/photo.webp" type="image/webp">
  <img src="/images/photo.jpg" alt="Description" width="800" height="600">
</picture>
```

Browsers that support AVIF use it. Browsers that support WebP but not AVIF use WebP. Older browsers fall back to JPEG. The `<img>` fallback is required.

For batch conversion, `sharp` in Node.js handles this efficiently:

```javascript
import sharp from 'sharp';
import { glob } from 'glob';

const images = await glob('public/images/**/*.{jpg,jpeg,png}');

for (const imagePath of images) {
  const base = imagePath.replace(/\.(jpg|jpeg|png)$/, '');
  
  await sharp(imagePath)
    .webp({ quality: 80 })
    .toFile(`${base}.webp`);
  
  await sharp(imagePath)
    .avif({ quality: 60 })
    .toFile(`${base}.avif`);
}
```

Quality 80 for WebP and 60 for AVIF are common starting points - visually lossless in most cases while achieving significant compression.

## Responsive images: serving the right size

A 1200px wide image served to a mobile device with a 400px viewport wastes 3x the bandwidth. Responsive images fix this:

```html
<img
  src="/images/photo-800.jpg"
  srcset="
    /images/photo-400.jpg  400w,
    /images/photo-800.jpg  800w,
    /images/photo-1200.jpg 1200w
  "
  sizes="
    (max-width: 600px) 100vw,
    (max-width: 1200px) 50vw,
    33vw
  "
  alt="Description"
  width="800"
  height="600"
>
```

`srcset` lists available sizes. `sizes` tells the browser how wide the image will be at different viewport widths. The browser calculates which source to fetch. On a 400px mobile screen, it fetches the 400px image instead of the 1200px one.

In Next.js, the `Image` component handles all of this automatically:

```jsx
import Image from 'next/image';

<Image
  src="/images/photo.jpg"
  alt="Description"
  width={800}
  height={600}
  sizes="(max-width: 768px) 100vw, 50vw"
/>
```

Next.js generates WebP/AVIF versions on demand, serves the appropriate size, and handles lazy loading.

## Lazy loading

Images below the fold do not need to load on initial page render. The `loading="lazy"` attribute defers their fetch until the user scrolls near them:

```html
<img src="/images/gallery-photo-1.jpg" alt="Gallery" loading="lazy" width="600" height="400">
```

This is a single attribute. Browser support is universal. Do not lazy-load images that are visible on initial load - that includes the hero image and any above-the-fold content. Lazy-loading the LCP image directly harms performance.

A rough rule: lazy-load images more than one screen height below the fold.

## Explicit dimensions

Always set `width` and `height` on images. The browser uses these to reserve space before the image loads, preventing layout shift (which affects CLS):

```html
<!-- Causes layout shift: content moves when image loads -->
<img src="/photo.jpg" alt="Photo">

<!-- Reserves space: no layout shift -->
<img src="/photo.jpg" alt="Photo" width="800" height="600">
```

With CSS, you can make the image responsive while still reserving the correct aspect ratio:

```css
img {
  width: 100%;
  height: auto;
}
```

The `height: auto` respects the intrinsic aspect ratio. The browser still knows the ratio from the HTML attributes and can reserve the right amount of space.

## Priority for the LCP image

The hero image typically is the Largest Contentful Paint element. It should load as early as possible. Add a preload hint and set `fetchpriority="high"`:

```html
<link rel="preload" as="image" href="/images/hero.webp" type="image/webp">

<img src="/images/hero.jpg" fetchpriority="high" alt="Hero" width="1200" height="600">
```

These two additions tell the browser to fetch the hero image at the highest priority, before most other resources. LCP improvements of 300-800ms are common from this change alone.

These optimizations - format conversion, responsive images, lazy loading, explicit dimensions, LCP preload - are not complex. They compound across every page view for every user.
