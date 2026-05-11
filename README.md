# yldzozgur.com

Personal site + blog. Built with [Astro](https://astro.build), deployed to GitHub Pages.

## Local development

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # production build → ./dist
npm run preview  # preview the production build
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

4. Commit and push to `main`. The GitHub Action will build and deploy automatically.

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
│   ├── writing/
│   │   ├── index.astro
│   │   └── [...slug].astro
│   └── rss.xml.js
└── styles/global.css

public/              # Static assets — favicon, CNAME, robots.txt
.github/workflows/   # CI/CD to GitHub Pages
```

## Deploy

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds the site
and publishes it to GitHub Pages.

### One-time setup

1. **Repo settings → Pages → Source**: set to "GitHub Actions".
2. **Repo settings → Pages → Custom domain**: enter `yldzozgur.com`.
3. **DNS at your registrar**: see DNS setup below.
4. Enable "Enforce HTTPS" once the certificate provisions (can take ~15 min).

### DNS records (at your domain registrar)

For an apex domain `yldzozgur.com`, add four `A` records pointing to GitHub Pages:

```
@   A   185.199.108.153
@   A   185.199.109.153
@   A   185.199.110.153
@   A   185.199.111.153
```

Plus a `CNAME` for the `www` subdomain:

```
www CNAME yldzozgur.github.io
```

The `public/CNAME` file in this repo tells GitHub Pages which custom domain to serve.

## License

Content (blog posts, `/about` text) — all rights reserved.
Code (templates, components, styles) — MIT.
