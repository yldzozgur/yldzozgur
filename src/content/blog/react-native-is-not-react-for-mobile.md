---
title: "React Native is not React for mobile. Here's what actually changes."
description: "React Native shares React's component model but runs in a fundamentally different environment. The differences that trip up web developers most often."
pubDate: 2025-01-27
tags: ["React Native", "Mobile"]
draft: false
---

## Same model, different platform

React Native uses the same component model, hooks, and state management patterns as React on the web. But it does not run in a browser. There is no DOM, no CSS, no `<div>`, and no `window`. The UI is rendered to native platform components -- UIView on iOS, View on Android.

Understanding what changed versus what stayed the same is the fastest path to productive React Native development.

## What stays the same

The React mental model transfers completely:

- Components are functions that return JSX
- `useState`, `useEffect`, `useContext`, `useReducer` all work identically
- Props, component composition, lifting state up -- same patterns
- Redux, Zustand, Jotai, React Query -- all work
- TypeScript support is first-class

If you understand React, you understand how to structure a React Native application.

## What changes: primitives

The JSX elements are different. Web elements do not exist in React Native.

| Web | React Native |
|-----|-------------|
| `<div>` | `<View>` |
| `<p>`, `<span>` | `<Text>` |
| `<img>` | `<Image>` |
| `<input>` | `<TextInput>` |
| `<button>` | `<TouchableOpacity>` or `<Pressable>` |
| `<ul>`, `<li>` | `<FlatList>` |
| `<a>` | No direct equivalent; use navigation |

Every piece of text must be inside a `<Text>` component. Rendering a plain string inside a `<View>` throws an error. This is one of the most common mistakes coming from web.

## What changes: styling

React Native uses StyleSheet objects, not CSS. The syntax looks like CSS but it's a subset -- no cascade, no inheritance (except font properties within nested `Text`), no pseudo-classes, no CSS grid.

```javascript
import { StyleSheet, View, Text } from 'react-native';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111',
  },
});

function Screen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Hello</Text>
    </View>
  );
}
```

Styles are JavaScript objects. Values are unitless numbers (they represent density-independent pixels) or strings for specific cases like `'50%'`. There is no `rem`, no `em`, no `vw`.

Flexbox is the layout system. The difference from web: `flexDirection` defaults to `column`, not `row`. More on that in another post.

## What changes: navigation

There is no URL bar and no browser history. Navigation between screens is managed entirely by a navigation library, with React Navigation being the standard choice.

```javascript
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator();

function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

Navigation is declarative but imperative navigation calls are different: `navigation.navigate('Profile', { userId: 42 })` instead of `<a href="/profile/42">`.

## What changes: platform differences

iOS and Android behave differently in ways that matter for UI. Date pickers look different, keyboard behavior differs, safe areas vary. React Native gives you `Platform.OS` to branch on platform-specific logic and allows platform-specific files (`.ios.js`, `.android.js`).

## What changes: no browser APIs

`fetch` works. `console.log` works. Most browser-specific APIs do not: no `localStorage` (use AsyncStorage), no `WebSocket` from the browser (React Native has its own), no `navigator.geolocation` in the same form, no `window`, no `document`.

## The actual learning curve

For an experienced React developer, the learning curve in React Native is not React -- it's the platform. Learning how iOS handles the keyboard, how the native navigation gesture interactors work, how permissions are requested, how to deal with safe areas and notches. That's the new territory, not the component model.
