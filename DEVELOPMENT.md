# yldzozgur.com — development

Personal site + blog. Built with [Astro](https://astro.build), deployed to Cloudflare Workers.

## Local development

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # production build → ./dist
npm run preview  # build + wrangler dev
```

Requires Node 18+ (Node 20 recommended).

## Writing a new blog post

1. Create a new markdown file in `src/content/blog/`. The filename becomes the URL slug:

   `src/content/blog/my-new-post.md` → `yldzozgur.com/writing/my-new-post`

2. Add the frontmatter:

   ```markdown
   ---
   title: "The post title"
   description: "Short summary, used for SEO and the listing page."
   pubDate: 2026-05-15
   tags: ["typescript", "career"]
   draft: false
   ---

   Your content here, in markdown.
   ```

3. Set `draft: true` while writing — draft posts won't be published.

4. Commit and push to `main`. Cloudflare Workers auto-builds and deploys.

## Project structure

```
src/
├── components/      # Header, Footer
├── content/blog/    # Markdown blog posts
├── content.config.ts # Blog schema (frontmatter shape)
├── layouts/         # BaseLayout, PostLayout
├── pages/           # Routes
│   ├── index.astro
│   ├── about.astro
│   ├── work.astro
│   ├── 404.astro
│   ├── writing/
│   │   ├── index.astro
│   │   ├── [...slug].astro
│   │   └── tags/
│   └── rss.xml.js
├── styles/global.css
└── ...

public/              # Static assets — favicon, og-default.png, projects/
wrangler.jsonc       # Cloudflare Workers config
astro.config.mjs     # Astro + Cloudflare adapter config
```

## Deploy

Pushing to `main` triggers a Cloudflare Workers build via the connected Git integration.
Worker name: `yldzozgur`. Custom domain: `yldzozgur.com` (DNS managed in Cloudflare).

### Environment variables

| Variable | Purpose |
|---|---|
| `PUBLIC_CF_ANALYTICS_TOKEN` | Cloudflare Web Analytics beacon token (optional). Set in Workers env to enable visitor tracking. |

## License

Content (blog posts, `/about` text) — all rights reserved.
Code (templates, components, styles) — MIT.
