---
title: "Reanimated: why React Native animations need a different model."
description: "React Native's built-in Animated API has limitations that Reanimated solves by running animations on the UI thread. The core concepts and when the difference matters."
pubDate: 2025-02-24
tags: ["React Native", "Mobile", "Animation"]
draft: false
---

## The JavaScript thread problem

React Native runs JavaScript on a background thread separate from the UI thread. The UI thread is responsible for rendering. Normally, they communicate via a bridge.

This architecture creates a problem for animations: if JavaScript is busy (running Redux reducers, parsing JSON, handling events), it can't send animation updates to the UI thread. The animation stutters while JavaScript catches up.

React Native's built-in `Animated` API partially addresses this with `useNativeDriver: true`, which offloads simple transform and opacity animations to the native side. But the interpolations and logic still originate in JavaScript.

## Reanimated's approach

React Native Reanimated (version 2 and later) takes a different approach: it moves animation logic to the UI thread entirely. Shared values are values that exist on both threads. Worklets are JavaScript functions that are serialized and run on the UI thread.

```javascript
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';

function ScaleButton({ onPress }) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  function handlePress() {
    scale.value = withSpring(0.95, {}, () => {
      scale.value = withSpring(1);
    });
    onPress();
  }

  return (
    <Animated.View style={animatedStyle}>
      <Pressable onPress={handlePress}>
        <Text>Press me</Text>
      </Pressable>
    </Animated.View>
  );
}
```

`useSharedValue` creates a value accessible on both threads. `useAnimatedStyle` is a worklet -- it runs on the UI thread, so it can read shared values and return styles without going through the bridge. `withSpring` drives the animation to its target value using a spring physics model.

## Gesture-driven animations

Where Reanimated really shines is gesture-driven animations. With `react-native-gesture-handler` and Reanimated together, swipe-to-dismiss, drag-to-reorder, and pull-to-refresh animations run entirely on the UI thread:

```javascript
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  runOnJS,
} from 'react-native-reanimated';

function SwipeableCard({ onDismiss }) {
  const translateX = useSharedValue(0);

  const panGesture = Gesture.Pan()
    .onChange(event => {
      translateX.value = event.translationX;
    })
    .onEnd(event => {
      if (Math.abs(event.velocityX) > 800 || Math.abs(translateX.value) > 150) {
        translateX.value = withSpring(Math.sign(translateX.value) * 500);
        runOnJS(onDismiss)();
      } else {
        translateX.value = withSpring(0);
      }
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
  }));

  return (
    <GestureDetector gesture={panGesture}>
      <Animated.View style={[styles.card, animatedStyle]}>
        {/* card content */}
      </Animated.View>
    </GestureDetector>
  );
}
```

The `onChange` and `onEnd` callbacks are worklets -- they run on the UI thread. `runOnJS` bridges back to JavaScript when you need to call a regular function like `onDismiss`.

## when to use Reanimated

Use Reanimated when:
- The animation is tied to a gesture (pan, swipe, pinch)
- The animation needs to respond to rapid value changes
- You're building a complex animation that needs 60fps without JavaScript interference

The built-in `Animated` with `useNativeDriver: true` is still fine for:
- Simple entrance/exit animations triggered by state changes
- Basic opacity and transform animations with no gesture interaction
- Cases where you want to minimize dependencies

Reanimated has a learning curve -- worklets have restrictions (no closures over non-worklet values, limited JavaScript APIs). But for gesture-driven UI, it's the only option that reliably performs well.
