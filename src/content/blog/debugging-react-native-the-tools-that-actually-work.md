---
title: "Debugging React Native: the tools that actually tell you what's wrong."
description: "A practical overview of the debugging tools available in React Native -- the built-in debugger, Flipper, React DevTools, and logging strategies that work in production."
pubDate: 2025-02-27
tags: ["React Native", "Mobile", "Debugging"]
draft: false
---

## The debugging landscape

React Native debugging is more fragmented than web debugging. There's no browser DevTools panel that does everything. Different tools cover different concerns, and knowing which tool to reach for saves significant time.

## The built-in developer menu

Shake the device (or press Cmd+D in iOS Simulator, Ctrl+M in Android emulator) to open the developer menu. The key options:

- **Reload**: refreshes the JavaScript bundle without rebuilding the native app
- **Open Debugger**: opens the JavaScript debugger (Chrome DevTools or the new Hermes debugger)
- **Show Element Inspector**: overlays layout bounds and lets you inspect component styles

For quick iterations, Reload is essential. For layout issues, the Element Inspector saves you from guessing which style is being applied.

## React Native DevTools (Hermes debugger)

Modern React Native (0.73+) uses Hermes as the JavaScript engine, which has its own debugger protocol. The React Native DevTools opens a Chrome DevTools-like interface with:

- Console output
- Breakpoints in JavaScript source
- Network request inspection
- Performance profiling

```bash
# Open via the terminal while the app is running
npx react-native start --experimental-debugger
```

Or use the "Open Debugger" option from the developer menu.

## Flipper

Flipper is a desktop debugging platform for React Native. It connects to a running app and provides plugins:

**Network plugin**: shows all outgoing HTTP requests and responses, including headers and body. More useful than console.log for inspecting API calls.

**React DevTools plugin**: full React component tree inspection, props, and state -- the same experience as the browser's React DevTools.

**Layout plugin**: inspect view hierarchy, measure dimensions, and see applied styles.

**Logs plugin**: console output from the JavaScript and native layers in one place.

Flipper requires installation on each developer machine and setup in the native code. The React Native DevTools (above) is increasingly replacing it for new projects.

## Console.log and remote debugging

`console.log` outputs to the Metro bundler terminal and to Flipper/DevTools. For quick value inspection it's fast, but excessive logging slows the app.

For structured logging in production, use a service like Sentry or Datadog. Adding crash reporting catches errors that users don't report:

```javascript
import * as Sentry from '@sentry/react-native';

Sentry.init({
  dsn: 'https://your-dsn@sentry.io/project-id',
});

// Errors are captured automatically
// Manual capture:
Sentry.captureException(error);
Sentry.captureMessage('Something unusual happened');
```

## Debugging native crashes

When the app crashes without a JavaScript error, the problem is in native code. For iOS, open Xcode's device logs (Window > Devices and Simulators) to see the crash report. For Android, use `adb logcat` in the terminal.

Most native crashes in React Native come from native modules, mismatched versions of libraries, or incorrect `Info.plist` configurations.

## Debugging network requests

For local development against a local server, check the device's network connectivity first. The iOS Simulator can use the Mac's network directly, but physical devices need the Mac's local IP:

```javascript
const BASE_URL = __DEV__
  ? 'http://192.168.1.100:3000'
  : 'https://api.production.com';
```

When a fetch fails silently, log the full error:

```javascript
try {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text();
    console.error(`HTTP ${res.status}:`, body);
  }
} catch (err) {
  console.error('Fetch error:', err.message, err);
}
```

## The most common debugging scenarios

**Red screen (JS error)**: read the stack trace. The file and line number are shown. The error is almost always in the component tree above the error boundary.

**White screen (blank app)**: usually a JavaScript error during startup before the UI renders. Check the Metro terminal for the error.

**Layout looks wrong**: use the Element Inspector or Flipper's Layout plugin to see computed styles and box model.

**Network request returns wrong data**: use Flipper Network or log `response.json()` before returning it.

**App crash (no error screen)**: check native logs in Xcode or `adb logcat`.
