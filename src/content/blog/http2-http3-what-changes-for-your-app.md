---
title: "HTTP/2 and HTTP/3: what changes for your app."
description: "How HTTP/2 multiplexing and HTTP/3's QUIC transport improve performance, and what these protocol changes mean for your application design."
pubDate: 2025-11-24
tags: ["HTTP", "Performance"]
draft: false
---

HTTP/1.1 has been the web's backbone since 1997. HTTP/2 arrived in 2015 and HTTP/3 in 2022. Both address real bottlenecks in HTTP/1.1. Understanding the changes tells you which performance patterns are obsolete and which new capabilities to use.

## The HTTP/1.1 bottlenecks

HTTP/1.1 can reuse TCP connections (keep-alive), but each request must complete before the next can start on the same connection -- this is called head-of-line blocking. To work around this, browsers open 6-8 parallel TCP connections per host. But each TCP connection has its own overhead, and you're still limited to 6-8 concurrent requests.

This limitation drove a set of HTTP/1.1 optimization techniques:
- **Domain sharding**: Spread resources across multiple subdomains to get more parallel connections
- **Image sprites**: Combine many images into one to reduce requests
- **CSS/JS concatenation**: Bundle many small files into fewer large ones
- **Inlining**: Embed CSS and small images directly in HTML to save a request

These are workarounds for protocol limitations, not good engineering.

## HTTP/2: multiplexing

HTTP/2 keeps a single TCP connection per host but allows multiple requests to be in flight simultaneously, with responses interleaved at the byte level. This is called multiplexing.

```
HTTP/1.1:
Connection 1: [req1 ----response1----] [req2 ----response2----]
Connection 2: [req3 ----response3----]
Connection 3: [req4 ----response4----]

HTTP/2:
Single connection: [req1][req2][req3][req4] [resp1-chunk][resp2-chunk][resp3-chunk][resp4-chunk]...
```

With multiplexing, the request-per-connection limit disappears. The browser can send hundreds of requests on a single connection.

This makes the HTTP/1.1 workarounds counterproductive under HTTP/2:
- **Domain sharding**: Now harmful. Multiple domains = multiple connections = no multiplexing benefit
- **File concatenation**: Large bundles that change frequently bust the cache entirely. Many small files can be cached individually
- **Inlining**: Prevents separate caching of the inlined resource

If your build process is still doing aggressive bundling and domain sharding as performance optimizations, check if your servers are actually using HTTP/2.

## HTTP/2 server push (deprecated)

HTTP/2 included a server push feature: the server could push resources it knows the client will need without waiting for a request. In practice, this was difficult to implement correctly, often sent resources the client already had cached, and Chrome removed support in 2022. Ignore it.

The replacement is the `Link` header with `rel=preload`:

```
Link: </styles.css>; rel=preload; as=style, </app.js>; rel=preload; as=script
```

This tells the browser to fetch these resources early, without the server initiating the transfer unsolicited.

## HTTP/3 and QUIC

HTTP/3 replaces TCP with QUIC (a UDP-based protocol developed by Google). This addresses a fundamental limitation of HTTP/2: even with multiplexing, a single TCP packet loss stalls all multiplexed streams while TCP retransmits. This is TCP head-of-line blocking.

QUIC tracks each stream independently. Packet loss in one stream doesn't block others.

Additional QUIC benefits:
- **Faster connection establishment**: QUIC combines the TLS handshake with the transport handshake, achieving connection setup in one round trip instead of two
- **Connection migration**: A QUIC connection survives IP address changes (e.g., switching from WiFi to cellular). TCP connections break and must restart
- **Built-in encryption**: QUIC requires TLS 1.3. There's no unencrypted QUIC

For most applications, HTTP/3 is transparent -- your CDN or load balancer handles it, and the browser negotiates the protocol automatically via the `Alt-Svc` header or HTTPS DNS records.

## Checking which protocol your app uses

In Chrome DevTools, Network tab, right-click the column headers and enable "Protocol". You'll see `h2` (HTTP/2), `h3` (HTTP/3), or `http/1.1`.

```bash
# Check via curl
curl -sI --http2 https://yoursite.com | grep -i "< HTTP"

# Check via openssl (shows negotiated ALPN protocol)
openssl s_client -connect yoursite.com:443 -alpn h2 2>&1 | grep ALPN
```

## Priority and resource hints

HTTP/2 supports stream prioritization. Browsers use this to request critical resources (HTML, render-blocking CSS) before lower-priority ones (images, analytics scripts).

You can influence prioritization with resource hints:

```html
<!-- Highest priority: critical CSS -->
<link rel="preload" href="/critical.css" as="style">

<!-- High priority: LCP image -->
<link rel="preload" href="/hero.jpg" as="image" fetchpriority="high">

<!-- Low priority: analytics -->
<script src="/analytics.js" fetchpriority="low" defer></script>
```

The `fetchpriority` attribute (supported in Chrome, Firefox, Safari) gives explicit hints to the browser's scheduler.

## What to do today

- **Enable HTTP/2 on your server/CDN**: Most managed platforms do this by default. If you're running your own nginx, enable `listen 443 ssl http2`
- **Stop domain sharding**: If you're still on a CDN config that spreads assets across subdomains for HTTP/1.1 performance, consolidate under one domain
- **Reconsider bundle strategy**: Smaller, more granular bundles take advantage of HTTP/2 multiplexing and improve cache granularity
- **HTTP/3**: Your CDN likely already supports it. Cloudflare, Fastly, and most major CDNs have had HTTP/3 enabled for years

The protocol improvements are mostly infrastructure concerns. The application-level impact is that the micro-optimizations built around HTTP/1.1 limitations are no longer necessary, and in some cases actively harmful.
