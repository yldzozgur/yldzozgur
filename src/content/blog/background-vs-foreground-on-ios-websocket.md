---
title: "Background vs foreground on iOS: what happens to your WebSocket."
description: "iOS aggressively suspends background apps to save battery. What that means for WebSocket connections and the strategies for handling the transition."
pubDate: 2025-03-03
tags: ["React-Native", "Mobile", "iOS", "WebSocket"]
draft: false
---

## iOS app lifecycle

iOS apps move through distinct states: Active (foreground, receiving events), Inactive (transitioning, like during a phone call), Background (running briefly), and Suspended (frozen, no code runs).

When a user presses the home button or switches to another app, your app moves to Background, runs briefly, then transitions to Suspended. In the Suspended state, no JavaScript runs -- no timers, no network callbacks, nothing.

This is fundamentally different from a browser tab, which continues running in the background.

## What happens to a WebSocket

When the app is suspended, the TCP connection underlying your WebSocket is dropped. The OS reclaims the file descriptor. Your server eventually detects the dead connection, but your client is frozen and doesn't know any of this happened.

When the user returns to the app (Foreground transition), JavaScript resumes and finds:

- The WebSocket object is in a `CLOSED` state
- Any messages sent while suspended are lost
- The server may have removed the client from any subscription lists

Without explicit handling, the app will appear to be "connected" (the old WebSocket state object exists) but silently receive nothing.

## Detecting the transition

React Native's `AppState` module notifies you when the app transitions between states:

```javascript
import { AppState } from 'react-native';
import { useEffect, useRef } from 'react';

function useAppStateWebSocket(url) {
  const wsRef = useRef(null);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    connect();

    const subscription = AppState.addEventListener('change', nextAppState => {
      const prevState = appState.current;
      appState.current = nextAppState;

      if (prevState.match(/inactive|background/) && nextAppState === 'active') {
        // App just came to foreground
        reconnect();
      }

      if (nextAppState.match(/inactive|background/)) {
        // App going to background
        gracefulDisconnect();
      }
    });

    return () => {
      subscription.remove();
      gracefulDisconnect();
    };
  }, []);

  function connect() {
    wsRef.current = new WebSocket(url);
    wsRef.current.onmessage = handleMessage;
    wsRef.current.onclose = handleClose;
    wsRef.current.onerror = handleError;
  }

  function reconnect() {
    if (wsRef.current?.readyState === WebSocket.CLOSED) {
      connect();
    }
  }

  function gracefulDisconnect() {
    wsRef.current?.close(1000, 'App backgrounded');
  }
}
```

The transition from `background` to `active` is the signal to reconnect.

## What to do before backgrounding

When you detect the app going to background, decide what to do with the connection:

**Close proactively**: send a clean close frame. The server knows the client is leaving. This is polite but means reconnecting on return.

**Do nothing**: let iOS kill the connection eventually. The server will time it out. Less clean, but simpler.

For most real-time features (chat, live updates, notifications), proactive close and reconnect on foreground is the right pattern.

## Missed messages

When the app returns to foreground and reconnects, it has missed all messages sent during suspension. How you handle this depends on the use case:

- **Chat**: fetch messages with a timestamp since last seen, then attach the WebSocket for new messages
- **Live data feed**: reconnect and receive only new data (historical data is stale)
- **Presence**: re-announce the client's presence to the server

The reconnection isn't just a socket reconnect -- it's often a partial re-initialization of state.

## Testing background transitions

In the iOS Simulator, use the Hardware menu > Home to simulate pressing the home button. The app goes to background. Switch back by tapping the app icon or using the app switcher. Watch your WebSocket state change through the transition.

A useful debug log:

```javascript
AppState.addEventListener('change', state => {
  console.log('App state changed to:', state);
  console.log('WebSocket state:', wsRef.current?.readyState);
});
```

The WebSocket readyState values are 0 (CONNECTING), 1 (OPEN), 2 (CLOSING), 3 (CLOSED).

