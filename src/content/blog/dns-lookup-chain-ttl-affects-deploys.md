---
title: "DNS: the lookup chain and the TTL that affects your deploys."
description: "How DNS resolution works step by step, what TTL means in practice, and why DNS propagation can hold up your deployments."
pubDate: 2025-11-03
tags: ["DevOps", "Networking"]
draft: false
---

DNS is the phone book of the internet. You ask for a hostname, you get an IP address. The lookup chain behind that simple exchange has multiple steps, caches at every level, and TTL values that directly affect how quickly your infrastructure changes take effect.

## The lookup chain

When you type `api.example.com` in a browser:

**1. Local DNS cache**: The OS checks its cache. If a recent lookup resolved this hostname and the TTL hasn't expired, it returns the cached IP immediately.

**2. Stub resolver**: If not cached, the OS queries its configured DNS resolver, usually provided by your router or ISP (e.g., `192.168.1.1`).

**3. Recursive resolver**: The stub resolver forwards to a recursive resolver (like `8.8.8.8` for Google DNS or `1.1.1.1` for Cloudflare). This resolver handles the full lookup chain.

**4. Root name servers**: The recursive resolver queries a root server (13 root server clusters). The root server says: "I don't know `api.example.com`, but `.com` is handled by these TLD name servers."

**5. TLD name servers**: The resolver queries a `.com` TLD name server. It says: "I don't know `api.example.com`, but `example.com` is handled by these authoritative name servers."

**6. Authoritative name servers**: The resolver queries example.com's authoritative name server. This is the actual source of truth -- it returns the IP address for `api.example.com`.

**7. Response cached and returned**: The recursive resolver caches the result (respecting TTL), returns it to the stub resolver, which returns it to the OS, which returns it to the browser.

The full chain happens only on a cache miss. On a cache hit at any level, the chain short-circuits.

## What TTL means

Every DNS record has a TTL (Time To Live) in seconds. When a resolver caches a record, it caches it for that many seconds. After expiry, the resolver must query the authoritative server again.

TTL is a server-side configuration, not client-side. You set it on your DNS records:

```
api.example.com  A   300   203.0.113.42
^hostname        ^type  ^TTL   ^value
```

TTL of 300 means resolvers and clients cache this record for 5 minutes.

**Common TTL values and tradeoffs:**

| TTL | Use case |
|-----|----------|
| 60 | Rapid changeover needed, frequent updates |
| 300 | Default for most records |
| 3600 | Stable records, improved performance |
| 86400 | Highly stable records (MX, long-lived infrastructure) |

Low TTL means DNS changes propagate quickly but every resolver must re-query more often. High TTL means faster resolution (cache hits) but changes are slow to propagate.

## Pre-deployment TTL reduction

This is the pattern that experienced ops teams use before every DNS change:

**1-2 days before the change**: Lower the TTL on records you'll be changing to 60 or 300 seconds.

Wait for the old high TTL to expire across all resolvers. Now all resolvers are caching for only 60 seconds.

**During the change**: Update the DNS record to the new IP.

Maximum time for the change to propagate: 60 seconds (the current TTL).

**After the change is stable**: Raise the TTL back to 3600.

If you skip this and change a record with a 24-hour TTL, some resolvers will serve the old IP for up to 24 hours.

## DNS record types

**A record**: Maps hostname to IPv4 address.
```
example.com  A  203.0.113.42
```

**AAAA record**: Maps hostname to IPv6 address.
```
example.com  AAAA  2001:db8::1
```

**CNAME record**: Maps hostname to another hostname. The resolver follows the chain to get the final IP.
```
www.example.com  CNAME  example.com
```

**MX record**: Mail server for a domain.

**TXT record**: Arbitrary text, used for domain verification and SPF/DKIM records.

**NS record**: Specifies the authoritative name servers for a domain. You change these when migrating DNS providers.

**SOA record**: Start of Authority, metadata about the zone including the default TTL.

## Verifying DNS with dig

```bash
# Query the A record for a domain
dig api.example.com A

# Query a specific resolver (bypass local cache)
dig @8.8.8.8 api.example.com A

# Query the authoritative name server directly
dig api.example.com A +trace

# Check the TTL remaining on a cached record
dig api.example.com A | grep -i ttl
```

The `+trace` flag shows the full resolution chain from root to authoritative server. Useful for debugging propagation issues.

## CNAME flattening

Root domains (apex) cannot use CNAME records in standard DNS -- a CNAME at `example.com` would conflict with the SOA and NS records required there. This is why CDNs and hosting providers often give you an IP to use as an A record for the apex.

Cloudflare and some other DNS providers support CNAME flattening: you configure a CNAME at the apex in their UI, but they return an A record (the resolved IP) for actual queries. This gives you the flexibility of CNAME (automatic IP updates) without the protocol violation.

## DNS and deploy timing

When you deploy to a new server IP and update DNS, users still hitting the old IP will get your old application. If the old server is still running, this is fine -- both serve the same app. If you shut down the old server too quickly, users with cached DNS still pointing to the old IP get connection errors.

The safe approach: keep the old server running for TTL + buffer time after a DNS change. For a 300 TTL record, wait at least 10 minutes after the DNS change before decommissioning the old server.
