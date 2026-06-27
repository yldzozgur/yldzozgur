---
title: "Platform-specific code: .ios.js files vs Platform.OS."
description: "React Native offers two ways to write platform-specific code: file extensions that the bundler resolves automatically, and the Platform API for inline branching."
pubDate: 2025-02-20
tags: ["React Native", "Mobile", "iOS"]
draft: false
---

## Two mechanisms, different use cases

React Native has two built-in ways to handle platform-specific code: platform-specific file extensions and the `Platform` module. They solve different scales of platform divergence.

## Platform.OS for small differences

When the platform difference is a single value, a style, or a small expression, the `Platform` API keeps everything in one file:

```javascript
import { Platform, StyleSheet } from 'react-native';

const styles = StyleSheet.create({
  header: {
    paddingTop: Platform.OS === 'ios' ? 44 : 24,
    backgroundColor: '#fff',
  },
  shadow: Platform.select({
    ios: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
    },
    android: {
      elevation: 4,
    },
  }),
});
```

`Platform.OS` is a string: `'ios'`, `'android'`, or `'web'`. `Platform.select` takes an object keyed by platform and returns the value for the current platform.

For conditional rendering:

```javascript
function DatePicker({ value, onChange }) {
  if (Platform.OS === 'ios') {
    return <IOSDatePicker value={value} onChange={onChange} />;
  }
  return <AndroidDatePicker value={value} onChange={onChange} />;
}
```

## Platform-specific files for large differences

When the difference between platforms is significant -- different components, different APIs, different behavior -- split the logic into separate files.

The bundler automatically resolves platform-specific extensions:

```
components/
  DatePicker.ios.js
  DatePicker.android.js
  DatePicker.js  (fallback for other platforms)
```

Any import of `DatePicker` will resolve to `DatePicker.ios.js` on iOS and `DatePicker.android.js` on Android:

```javascript
import DatePicker from './components/DatePicker';
// Bundler picks the right file automatically
```

The component API should be identical in both files -- same props, same behavior. Platform differences are implementation details.

```javascript
// DatePicker.ios.js
import DateTimePicker from '@react-native-community/datetimepicker';

export default function DatePicker({ value, onChange }) {
  return (
    <DateTimePicker
      value={value}
      mode="date"
      display="spinner"
      onChange={(event, date) => onChange(date)}
    />
  );
}

// DatePicker.android.js
import DateTimePicker from '@react-native-community/datetimepicker';

export default function DatePicker({ value, onChange }) {
  return (
    <DateTimePicker
      value={value}
      mode="date"
      display="calendar"
      onChange={(event, date) => date && onChange(date)}
    />
  );
}
```

## Native module platform files

The same file extension mechanism works for native module code. If you're writing a native module with a JavaScript interface:

```
NativeCamera.ios.js
NativeCamera.android.js
```

Each file wraps the platform-specific native module with a unified JavaScript API. Consumers never know which platform they're on.

## Platform.Version for version-specific code

For iOS, `Platform.Version` is a string like `'16.4'`. For Android, it's a number (the SDK version).

```javascript
if (Platform.OS === 'ios' && parseInt(Platform.Version, 10) >= 16) {
  // Use iOS 16+ specific API
}

if (Platform.OS === 'android' && Platform.Version >= 31) {
  // Use Android 12+ API
}
```

## The decision rule

Use `Platform.OS` when:
- The difference is a few lines
- It's a style value, a prop, or a small conditional

Use platform-specific files when:
- The component structure is significantly different
- The file would be cluttered with `Platform.select` calls
- You want to isolate testing -- test each platform file independently

A good heuristic: if you find yourself writing more than three `Platform.OS` checks in a single component, the component probably wants to be split.
