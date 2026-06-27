---
title: "AsyncStorage: client-side persistence without a database."
description: "AsyncStorage is React Native's equivalent of localStorage -- a simple key-value store for persisting data on the device. How it works and when to use it."
pubDate: 2025-02-13
tags: ["React-Native", "Mobile"]
draft: false
---

## What AsyncStorage is

AsyncStorage is a simple, asynchronous key-value store for React Native. It persists data to the device's local storage -- the data survives app restarts, but is cleared when the app is uninstalled.

It's the closest equivalent to `localStorage` in the browser, with one key difference: all operations are asynchronous. There is no synchronous read.

The community package `@react-native-async-storage/async-storage` is the standard choice (the built-in version was deprecated in 2020).

```bash
npm install @react-native-async-storage/async-storage
```

## Basic operations

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Write
await AsyncStorage.setItem('user_token', 'abc123');

// Read
const token = await AsyncStorage.getItem('user_token');
// Returns null if key doesn't exist

// Delete
await AsyncStorage.removeItem('user_token');

// Clear everything
await AsyncStorage.clear();
```

AsyncStorage only stores strings. For objects, serialize with JSON:

```javascript
// Write an object
const settings = { theme: 'dark', language: 'en', notifications: true };
await AsyncStorage.setItem('settings', JSON.stringify(settings));

// Read it back
const raw = await AsyncStorage.getItem('settings');
const settings = raw ? JSON.parse(raw) : null;
```

## Batch operations

For reading or writing multiple keys at once, batch operations are more efficient than multiple individual calls:

```javascript
// Read multiple keys
const keys = ['user_id', 'user_token', 'last_seen'];
const results = await AsyncStorage.multiGet(keys);
// results: [['user_id', '42'], ['user_token', 'abc'], ['last_seen', '...']]

const data = Object.fromEntries(results);

// Write multiple keys
await AsyncStorage.multiSet([
  ['user_id', '42'],
  ['user_token', 'abc123'],
  ['last_seen', new Date().toISOString()],
]);

// Remove multiple keys
await AsyncStorage.multiRemove(['user_id', 'user_token']);
```

## Common use cases

**Persisting auth tokens:**
```javascript
async function saveAuthToken(token) {
  await AsyncStorage.setItem('@auth_token', token);
}

async function getAuthToken() {
  return AsyncStorage.getItem('@auth_token');
}

async function clearAuthToken() {
  return AsyncStorage.removeItem('@auth_token');
}
```

The `@` prefix in keys is a convention to namespace your app's data and avoid collisions.

**Caching API responses:**
```javascript
const CACHE_KEY = '@posts_cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function getCachedPosts() {
  const raw = await AsyncStorage.getItem(CACHE_KEY);
  if (!raw) return null;

  const { data, timestamp } = JSON.parse(raw);
  if (Date.now() - timestamp > CACHE_TTL) {
    await AsyncStorage.removeItem(CACHE_KEY);
    return null;
  }
  return data;
}

async function cachePosts(posts) {
  await AsyncStorage.setItem(CACHE_KEY, JSON.stringify({
    data: posts,
    timestamp: Date.now(),
  }));
}
```

**Persisting user preferences:**
```javascript
const PREFS_KEY = '@user_prefs';

async function loadPreferences() {
  const raw = await AsyncStorage.getItem(PREFS_KEY);
  return raw ? JSON.parse(raw) : { theme: 'light', fontSize: 'medium' };
}

async function savePreferences(prefs) {
  await AsyncStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}
```

## Limitations

AsyncStorage is not encrypted. Sensitive data (passwords, financial information) should use the device's secure storage instead -- `expo-secure-store` or `react-native-keychain`.

AsyncStorage is not a database. It has no query capability. If you need to search, sort, or relate data, use a local database like WatermelonDB or SQLite.

Storage limits vary by platform. iOS has a default per-item limit of around 6MB and there's no documented maximum total. Android limits depend on the device. For large datasets, use a proper storage solution.

## Error handling

AsyncStorage operations can fail (storage full, device issues). Always wrap in try/catch for production code:

```javascript
async function safeGet(key) {
  try {
    return await AsyncStorage.getItem(key);
  } catch (error) {
    console.error('AsyncStorage read error:', error);
    return null;
  }
}
```

For small amounts of non-critical data -- auth tokens, preferences, onboarding state, recent searches -- AsyncStorage is the right choice. Simple, fast, zero configuration.

