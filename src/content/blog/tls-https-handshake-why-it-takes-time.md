---
title: "TLS/HTTPS: what happens in the handshake and why it takes time."
description: "A step-by-step look at the TLS handshake, what each round trip accomplishes, and how TLS 1.3 and session resumption reduce the cost."
pubDate: 2025-10-30
tags: ["Security", "HTTP"]
draft: false
---

Every HTTPS connection starts with a TLS handshake before a single byte of application data is exchanged. Understanding the handshake explains why the first request to a new server has higher latency, and why improvements like TLS 1.3 and session resumption matter.

## What TLS does

TLS (Transport Layer Security) provides three things:
1. **Encryption**: Data is encrypted in transit; eavesdroppers see ciphertext
2. **Authentication**: The server proves its identity via a certificate
3. **Integrity**: Data cannot be modified in transit without detection

HTTP over TLS is HTTPS. The HTTP protocol itself doesn't change; TLS is a layer underneath it.

## TLS 1.2 handshake (the older version)

Before application data flows, TLS 1.2 requires **2 round trips**:

**Round trip 1:**
1. Client sends `ClientHello`: supported TLS version, supported cipher suites, random bytes
2. Server responds with `ServerHello`: chosen cipher suite, server random bytes
3. Server sends certificate (public key + identity proof signed by a CA)
4. Server sends `ServerHelloDone`

**Round trip 2:**
5. Client verifies the certificate against trusted CAs
6. Client generates a pre-master secret, encrypts it with the server's public key, sends it
7. Client sends `ChangeCipherSpec` and `Finished`
8. Server decrypts the pre-master secret, derives session keys
9. Server sends `ChangeCipherSpec` and `Finished`

Only after step 9 can the client send the HTTP request.

With a 50ms round-trip time (reasonable for same-continent connections), TLS 1.2 adds 100ms of overhead before the first byte of your HTTP request is sent.

## TLS 1.3 handshake (the current version)

TLS 1.3, standardized in 2018, reduces the handshake to **1 round trip**:

**Round trip 1:**
1. Client sends `ClientHello` with supported cipher suites AND key share data (Diffie-Hellman public key)
2. Server can immediately compute the shared secret from the client's key share
3. Server sends `ServerHello` with its own key share, certificate, and `Finished`
4. Client verifies, sends `Finished`, and can immediately start sending HTTP data

The client can send application data immediately after receiving the server's response, without a second round trip. 50ms round trip overhead instead of 100ms.

## 0-RTT resumption: zero handshake overhead

For connections to servers the client has connected to before, TLS 1.3 supports 0-RTT (Zero Round Trip Time) resumption. The client can send application data in its very first message:

```
Client → Server: ClientHello + early_data (HTTP request) → 
Server → Client: ServerHello + HTTP response
```

The client uses a session ticket from the previous connection to encrypt the early data. This makes reconnecting to a server virtually free from a latency perspective.

**Security caveat**: 0-RTT data has no forward secrecy against replay attacks. An attacker who captures the encrypted data could replay the early data later. This is acceptable for GET requests (idempotent) but not for POST requests that cause side effects. Servers should reject non-safe methods in 0-RTT context.

## Certificate verification

After receiving the server's certificate, the client must verify it:

1. The certificate was signed by a trusted Certificate Authority (CA)
2. The certificate is for the hostname being connected to
3. The certificate hasn't expired
4. The certificate hasn't been revoked

Steps 1-3 are local checks. Step 4 is where things get interesting.

**OCSP (Online Certificate Status Protocol)**: The client contacts the CA's OCSP server to check revocation status. This adds another network request and round trip.

**OCSP Stapling**: The server includes a signed OCSP response ("staple") in the TLS handshake, eliminating the extra round trip. Servers should enable this.

**Certificate Transparency**: Modern browsers also check that certificates appear in public CT logs, but this is handled by the CA at issuance, not during the handshake.

## The full TCP + TLS timeline

For a new HTTPS connection:

```
0ms:    SYN (client → server)
50ms:   SYN-ACK (server → client)  [TCP handshake complete]
50ms:   ACK + ClientHello (client → server)
100ms:  ServerHello + Certificate + Finished (server → client) [TLS 1.3]
100ms:  Finished + HTTP GET (client → server)
150ms:  HTTP 200 response (server → client)
```

Total: 150ms to first byte of response on a 50ms RTT connection. Compare to 50ms for a plain HTTP request over an existing connection.

This is why connection reuse matters so much. HTTP/1.1 keep-alive and HTTP/2 multiplexing amortize the TCP+TLS cost across many requests.

## What you can do

**Enable TLS 1.3**: Most modern CDNs and cloud providers default to it. Verify your server configuration includes TLS 1.3.

**Enable OCSP Stapling**: Eliminates the revocation check round trip.

**Use a CDN with edge PoPs**: A CDN terminates TLS at the edge server close to the user. The TLS round trips happen over 5ms instead of 100ms, even if the CDN then makes its own slower request to your origin.

**Enable HTTP/2 or HTTP/3**: Reuse connections across multiple requests so the TLS overhead is paid once.

**Use session tickets**: TLS session resumption lets returning clients reconnect without a full handshake. Modern servers enable this by default.

For most applications, using Vercel, Cloudflare, or another managed platform handles all of this correctly without manual configuration. The important thing is understanding why HTTPS has higher initial latency than HTTP so you can appreciate what the infrastructure is doing on your behalf.
