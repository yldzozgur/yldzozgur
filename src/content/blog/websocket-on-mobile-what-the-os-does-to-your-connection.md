---
title: "WebSocket on mobile: what the OS does to your connection in the background."
description: "Mobile operating systems aggressively manage connections when an app is backgrounded. What iOS and Android do to your WebSocket and how to handle it."
pubDate: 2025-04-03
tags: ["WebSocket", "React-Native", "Mobile", "iOS"]
draft: false
---

## The mobile OS is not a passive host

On desktop, an open WebSocket connection stays open as long as the process is running. On mobile, the OS actively manages connections to preserve battery and memory. This creates a different set of problems than web developers typically encounter.

## iOS: suspension kills connections

When an iOS app moves to the background:

1. The app runs briefly to complete any in-flight work
2. After a few seconds, the app is suspended (completely frozen)
3. The OS may close TCP connections that belong to suspended apps
4. The server's heartbeat pings go unanswered -- the server eventually terminates the connection

When the user returns to the app:

1. The app resumes from the suspended state
2. JavaScript continues from where it left off
3. The WebSocket object has readyState `CLOSED`
4. The app appears to be connected but receives nothing

Without handling this, the user sees stale data or no updates until they manually refresh.

## Android: more lenient but not guaranteed

Android is more permissive than iOS with background execution. Apps can run longer in the background, and WebSocket connections can survive short backgrounding periods. However, Android's Doze mode (when the device has been still and unplugged for a while) restricts network access, which can kill connections in the same way.

The behavior also varies significantly by device manufacturer. Some Android OEMs (Xiaomi, Huawei) aggressively kill background processes beyond what stock Android does.

## Detecting the foreground transition

React Native's `AppState` module is the mechanism for detecting transitions:

```javascript
import { AppState } from 'react-native';
import { useEffect, useRef } from 'react';

function useReliableWebSocket(url, onMessage) {
  const wsRef = useRef(null);
  const appStateRef = useRef(AppState.currentState);

  function connect() {
    wsRef.current?.close();
    wsRef.current = new WebSocket(url);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
    };

    wsRef.current.onmessage = (e) => {
      onMessage(JSON.parse(e.data));
    };

    wsRef.current.onclose = () => {
      // Don't reconnect if app is going to background
      if (appStateRef.current === 'active') {
        // Unexpected close -- schedule reconnect
        setTimeout(connect, 3000);
      }
    };
  }

  useEffect(() => {
    connect();

    const subscription = AppState.addEventListener('change', nextState => {
      const prevState = appStateRef.current;
      appStateRef.current = nextState;

      if (prevState.match(/inactive|background/) && nextState === 'active') {
        // Returning to foreground -- reconnect
        connect();
      }
    });

    return () => {
      subscription.remove();
      wsRef.current?.close(1000, 'Component unmounted');
    };
  }, [url]);

  return wsRef;
}
```

## Handling missed messages after reconnect

Reconnecting restores the transport. It doesn't restore the application state. Messages sent while the app was suspended are lost.

The standard pattern is to request a state sync on reconnect:

```javascript
wsRef.current.onopen = () => {
  // Request any messages we missed since we were last active
  wsRef.current.send(JSON.stringify({
    type: 'sync',
    since: lastMessageTimestamp,
  }));
};
```

The server sends back a batch of missed messages or events, then switches to live streaming. This ensures no data is lost across the background transition.

## Push notifications as a fallback

For truly critical notifications (incoming messages, alerts), push notifications (APNs on iOS, FCM on Android) are the correct mechanism, not WebSockets. Push notifications are delivered by the OS even when the app is completely terminated.

WebSocket is for live, bidirectional communication while the app is active. Push notifications are for reaching the user when the app is not running. A complete real-time application uses both.

## Testing the transition

On the iOS Simulator:
1. Open the app
2. Establish a WebSocket connection
3. Press Cmd+H (home button)
4. Wait 10-15 seconds
5. Open the app again
6. Check if the WebSocket reconnected correctly

A bug here is usually the WebSocket `readyState` being `CLOSED` but the UI not knowing to reconnect.

