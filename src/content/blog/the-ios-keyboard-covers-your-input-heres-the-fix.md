---
title: "The iOS keyboard covers your input. Here's the fix."
description: "When the iOS keyboard opens, it can cover the TextInput the user is typing into. The correct fix depends on your layout, and there are several approaches."
pubDate: 2025-02-06
tags: ["React-Native", "Mobile", "iOS"]
draft: false
---

## The problem

When a user taps a `TextInput` on iOS, the keyboard slides up from the bottom of the screen. If that input is near the bottom of the layout, the keyboard covers it. The user is typing but can't see what they're typing.

This doesn't happen automatically on Android -- Android shifts the view up. On iOS, the behavior depends on how the layout is set up.

## KeyboardAvoidingView

React Native's built-in solution is `KeyboardAvoidingView`. It adjusts its layout in response to the keyboard appearing.

```javascript
import { KeyboardAvoidingView, Platform, TextInput, StyleSheet } from 'react-native';

function LoginScreen() {
  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <TextInput
        style={styles.input}
        placeholder="Email"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
      />
    </KeyboardAvoidingView>
  );
}
```

The `behavior` prop matters:

- `padding`: adds padding to the bottom of the container when the keyboard opens, pushing content up
- `height`: reduces the height of the container
- `position`: adjusts the absolute position of the container

On iOS, `padding` is usually the most reliable. On Android, `height` or no `KeyboardAvoidingView` at all often works better -- Android handles this natively.

## The keyboardOffset issue

If your screen has a header (from React Navigation), `KeyboardAvoidingView` doesn't know about it by default. The header height needs to be accounted for:

```javascript
import { useHeaderHeight } from '@react-navigation/elements';

function FormScreen() {
  const headerHeight = useHeaderHeight();

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior="padding"
      keyboardVerticalOffset={headerHeight}
    >
      {/* content */}
    </KeyboardAvoidingView>
  );
}
```

Without `keyboardVerticalOffset`, the view pushes up by the keyboard height but doesn't account for the space already taken by the header, so the content overshoots.

## ScrollView + keyboard dismiss

For forms inside a `ScrollView`, a different approach works well: scroll the focused input into view automatically.

```javascript
import { ScrollView, KeyboardAvoidingView, Platform } from 'react-native';

function SignupForm() {
  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ paddingBottom: 40 }}
      >
        {/* Many form fields */}
        <TextInput placeholder="First name" />
        <TextInput placeholder="Last name" />
        <TextInput placeholder="Email" />
        <TextInput placeholder="Password" />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
```

`keyboardShouldPersistTaps="handled"` ensures taps on buttons inside the ScrollView work while the keyboard is up, rather than just dismissing the keyboard.

The `paddingBottom` on `contentContainerStyle` ensures the last input is reachable even with the keyboard visible.

## react-native-keyboard-controller

For complex layouts where `KeyboardAvoidingView` is inconsistent, the third-party library `react-native-keyboard-controller` provides a more reliable implementation with smooth animations matching the keyboard animation curve.

```javascript
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';

// Drop-in replacement with better behavior
function Screen() {
  return (
    <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }}>
      {/* content */}
    </KeyboardAvoidingView>
  );
}
```

It uses native keyboard event listeners for frame-perfect animations, which the built-in component doesn't achieve consistently.

## Dismissing the keyboard

For screens where tapping outside a TextInput should dismiss the keyboard:

```javascript
import { TouchableWithoutFeedback, Keyboard, View } from 'react-native';

function Screen() {
  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
      <View style={{ flex: 1 }}>
        {/* content */}
      </View>
    </TouchableWithoutFeedback>
  );
}
```

Or use the `ScrollView` `keyboardDismissMode` prop:

```javascript
<ScrollView keyboardDismissMode="on-drag">
  {/* content */}
</ScrollView>
```

`on-drag` dismisses the keyboard when the user starts scrolling -- natural mobile behavior.

The keyboard problem has no single universal solution. For simple screens, the built-in `KeyboardAvoidingView` with `padding` behavior and a `keyboardVerticalOffset` for headers covers most cases.

