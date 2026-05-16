<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title><xsl:value-of select="/rss/channel/title"/> · RSS feed</title>
        <style>
          * { box-sizing: border-box; }
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 720px;
            margin: 0 auto;
            padding: 3rem 1.5rem;
            color: #18181b;
            line-height: 1.55;
            background: #fafaf9;
          }
          .badge {
            display: inline-block;
            background: linear-gradient(135deg, #f97316, #ea580c);
            color: white;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
            letter-spacing: 0.04em;
          }
          h1 {
            font-size: 2rem;
            margin: 0 0 0.5rem;
            letter-spacing: -0.02em;
          }
          .desc { color: #71717a; margin-bottom: 2rem; }
          .how {
            background: white;
            border: 1px solid #e4e4e7;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2.5rem;
          }
          .how h2 { font-size: 1.1rem; margin: 0 0 0.75rem; }
          .how ol { padding-left: 1.2rem; color: #3f3f46; }
          .how li { margin-bottom: 0.5rem; }
          .how a { color: #f97316; }
          code {
            background: #f4f4f5;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.85em;
            color: #18181b;
          }
          .items-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: #71717a;
            letter-spacing: 0.08em;
            margin-bottom: 1rem;
            font-weight: 600;
          }
          .item {
            background: white;
            border: 1px solid #e4e4e7;
            padding: 1.25rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 0.75rem;
            transition: border-color 0.2s, transform 0.2s;
          }
          .item:hover {
            border-color: #f97316;
            transform: translateY(-1px);
          }
          .item h3 { margin: 0 0 0.4rem; font-size: 1.05rem; }
          .item h3 a { color: #18181b; text-decoration: none; }
          .item h3 a:hover { color: #f97316; }
          .item time {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.75rem;
            color: #a1a1aa;
            display: block;
            margin-bottom: 0.5rem;
          }
          .item p { margin: 0; color: #52525b; font-size: 0.9rem; }
          .back {
            display: inline-block;
            margin-top: 2rem;
            color: #71717a;
            text-decoration: none;
            font-size: 0.875rem;
          }
          .back:hover { color: #18181b; }
        </style>
      </head>
      <body>
        <div class="badge">RSS · Feed</div>
        <h1><xsl:value-of select="/rss/channel/title"/></h1>
        <p class="desc"><xsl:value-of select="/rss/channel/description"/></p>

        <div class="how">
          <h2>How to subscribe</h2>
          <ol>
            <li>Copy this URL: <code><xsl:value-of select="/rss/channel/link"/>rss.xml</code></li>
            <li>Paste it into any RSS reader:
              <a href="https://feedly.com" target="_blank">Feedly</a>,
              <a href="https://www.inoreader.com" target="_blank">Inoreader</a>,
              <a href="https://reederapp.com" target="_blank">Reeder</a>,
              <a href="https://netnewswire.com" target="_blank">NetNewsWire</a>, etc.</li>
            <li>New posts appear automatically, no email signup needed.</li>
          </ol>
        </div>

        <p class="items-title">Latest posts</p>
        <xsl:for-each select="/rss/channel/item">
          <div class="item">
            <time>
              <xsl:value-of select="substring(pubDate, 0, 17)"/>
            </time>
            <h3>
              <a hreflang="en">
                <xsl:attribute name="href"><xsl:value-of select="link"/></xsl:attribute>
                <xsl:value-of select="title"/>
              </a>
            </h3>
            <p><xsl:value-of select="description"/></p>
          </div>
        </xsl:for-each>

        <a href="/" class="back">← Back to yldzozgur.com</a>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
