---
title: "Networking in React Native: the fetch quirks nobody documents."
description: "React Native supports fetch and XMLHttpRequest, but there are platform-specific quirks around SSL, timeouts, and iOS App Transport Security that catch developers off guard."
pubDate: 2025-02-17
tags: ["React-Native", "Mobile", "Networking"]
draft: false
---

## fetch works, mostly

React Native polyfills the browser's `fetch` API. Basic GET and POST requests work exactly as they do on the web:

```javascript
const response = await fetch('https://api.example.com/users');
const data = await response.json();
```

But several things behave differently from the browser, and some fail silently in ways that take time to track down.

## iOS App Transport Security

By default, iOS blocks HTTP (non-HTTPS) connections. This is App Transport Security (ATS), and it applies to any fetch call, XHR, or WebSocket using `ws://` instead of `wss://`.

If you're hitting a local development server over HTTP, you'll get a silent failure in production and a log warning in development. The fix for development is an exception in `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
  <key>NSAllowsLocalNetworking</key>
  <true/>
</dict>
```

`NSAllowsLocalNetworking` allows HTTP for localhost and `.local` domains without disabling ATS globally. Do not use `NSAllowsArbitraryLoads: true` in production -- it bypasses ATS for all connections and App Store review may flag it.

## No automatic timeout

Browser `fetch` has no built-in timeout, and neither does React Native's. A request to an unreachable server hangs indefinitely. On mobile, where networks are flaky, this matters.

Implement a timeout using `AbortController`:

```javascript
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs}ms`);
    }
    throw error;
  }
}
```

## FormData and file uploads

File uploads with `FormData` work, but the field names must be correct and the `Content-Type` header should not be set manually -- React Native sets it automatically with the correct boundary.

```javascript
async function uploadAudio(uri) {
  const formData = new FormData();

  formData.append('file', {
    uri,
    name: 'recording.m4a',
    type: 'audio/m4a',
  });

  const response = await fetch('https://api.example.com/upload', {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type: multipart/form-data manually
    // React Native sets it with the correct boundary automatically
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.json();
}
```

The file object needs `uri`, `name`, and `type`. The `uri` comes from the device file system or a recording module.

## Network state detection

Unlike the browser, React Native lets you check network connectivity before making requests:

```javascript
import NetInfo from '@react-native-community/netinfo';

const state = await NetInfo.fetch();
if (!state.isConnected) {
  throw new Error('No network connection');
}

// Or subscribe to changes
const unsubscribe = NetInfo.addEventListener(state => {
  console.log('Connection type', state.type);
  console.log('Is connected?', state.isConnected);
});
```

This is useful for showing offline states gracefully instead of letting requests fail with cryptic errors.

## localhost in the simulator and on device

In the iOS Simulator, `localhost` and `127.0.0.1` work and point to your Mac's local server. On a physical device connected to the same WiFi, you need your Mac's local IP address instead:

```javascript
const API_BASE = __DEV__
  ? 'http://192.168.1.100:3000'  // your Mac's IP
  : 'https://api.yourapp.com';
```

The `__DEV__` global is `true` in development builds and `false` in production.

## Certificate pinning

For high-security applications, certificate pinning ensures the app only communicates with servers presenting a known certificate. React Native's built-in `fetch` doesn't support this natively. Libraries like `react-native-ssl-pinning` provide a drop-in `fetch` replacement with pinning support.

## Debugging network requests

Flipper's Network plugin shows all outgoing requests and responses in development. React Native Debugger also intercepts network calls. For production debugging, integrating an error tracking service that logs failed requests is essential.

