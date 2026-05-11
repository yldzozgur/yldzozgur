import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const posts = await getCollection('blog', ({ data }) => !data.draft);

  return rss({
    title: 'Özgür Yıldız — Writing',
    description: 'Notes on TypeScript, Node.js, React, and shipping real software.',
    site: context.site,
    items: posts
      .sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
      .map((post) => ({
        title: post.data.title,
        description: post.data.description,
        pubDate: post.data.pubDate,
        link: `/writing/${post.id}/`,
        categories: post.data.tags,
      })),
    customData: `<language>en-us</language>`,
  });
}
