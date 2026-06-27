---
title: "Microphone permission on iOS: the request flow and the edge cases."
description: "How iOS microphone permissions work, when the system dialog appears, what happens when users deny it, and how to handle all the states in a React Native app."
pubDate: 2025-02-10
tags: ["React-Native", "Mobile", "iOS"]
draft: false
---

## iOS permissions are one-shot

On iOS, the system permission dialog appears exactly once per permission type. If the user taps "Don't Allow", the dialog never appears again. Future requests are silently denied. There is no second chance unless the user manually goes to Settings.

This makes the request flow important. You need to ask at the right moment, with enough context, so the user understands why the app needs the microphone.

## Info.plist requirement

Before any permission request can work, add a usage description to `ios/YourApp/Info.plist`:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>This app uses the microphone to record voice notes.</string>
```

This string appears in the system dialog. A specific, honest description increases grant rates. "This app needs microphone access" is unhelpful. "Record voice notes and transcriptions" tells the user what they get in exchange.

## Checking and requesting with expo-av or react-native-permissions

With `expo-av`:

```javascript
import { Audio } from 'expo-av';

async function requestMicrophonePermission() {
  const { status } = await Audio.requestPermissionsAsync();
  return status === 'granted';
}

async function checkMicrophonePermission() {
  const { status } = await Audio.getPermissionsAsync();
  return status; // 'granted' | 'denied' | 'undetermined'
}
```

With `react-native-permissions` (more granular control):

```javascript
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';

async function getMicrophoneStatus() {
  const result = await check(PERMISSIONS.IOS.MICROPHONE);
  // RESULTS.GRANTED | RESULTS.DENIED | RESULTS.BLOCKED | RESULTS.UNAVAILABLE
  return result;
}

async function requestMicrophoneAccess() {
  const result = await request(PERMISSIONS.IOS.MICROPHONE);
  return result;
}
```

The key distinction `react-native-permissions` makes: `DENIED` means the user hasn't decided yet (the dialog will appear on next request). `BLOCKED` means the user denied and won't be asked again. This distinction is important for UI logic.

## The complete permission flow

```javascript
import { check, request, PERMISSIONS, RESULTS, openSettings } from 'react-native-permissions';
import { Alert, Platform } from 'react-native';

async function ensureMicrophoneAccess() {
  if (Platform.OS !== 'ios') {
    // Android has a different permission key
    return handleAndroidMic();
  }

  const status = await check(PERMISSIONS.IOS.MICROPHONE);

  if (status === RESULTS.GRANTED) {
    return true;
  }

  if (status === RESULTS.DENIED) {
    // Haven't asked yet -- ask now
    const requestResult = await request(PERMISSIONS.IOS.MICROPHONE);
    return requestResult === RESULTS.GRANTED;
  }

  if (status === RESULTS.BLOCKED) {
    // User denied permanently -- guide them to Settings
    Alert.alert(
      'Microphone Required',
      'Please enable microphone access in Settings to use this feature.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Open Settings', onPress: openSettings },
      ]
    );
    return false;
  }

  return false;
}
```

## When to ask

Do not ask for microphone permission on app launch. Ask when the user takes an action that needs it -- tapping a "Record" button, starting a voice chat, pressing a microphone icon.

The pattern is:

1. User taps the action
2. Check current permission status
3. If `undetermined`: trigger the system dialog
4. If `granted`: proceed
5. If `blocked`: show an alert with a "Go to Settings" button

## Handling the return from Settings

When a user goes to Settings and grants permission, they return to the app. The app state doesn't automatically know the permission changed. Use `AppState` to re-check when the app comes back to the foreground:

```javascript
import { AppState } from 'react-native';

useEffect(() => {
  const subscription = AppState.addEventListener('change', nextState => {
    if (nextState === 'active') {
      checkMicrophonePermission().then(setPermissionStatus);
    }
  });
  return () => subscription.remove();
}, []);
```

This re-runs the permission check when the user returns from the Settings app, so the UI updates without requiring a restart.

## Testing permission states

The iOS Simulator lets you reset permissions via Device menu > Reset Location & Privacy. This brings the permission back to `undetermined` so you can test the dialog flow again. For testing the `blocked` state, deny the permission and try to access it again.

