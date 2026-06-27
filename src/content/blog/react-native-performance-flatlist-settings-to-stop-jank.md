---
title: "React Native performance: the FlatList settings that stop jank."
description: "FlatList is the standard way to render large lists in React Native, but its default settings aren't optimal for all cases. The props that make the biggest performance difference."
pubDate: 2025-03-06
tags: ["React Native", "Mobile", "Performance"]
draft: false
---

## Why lists are a performance hotspot

Rendering a long list of items is one of the most common sources of jank in React Native apps. The JavaScript thread renders components, the bridge sends them to the native side, and the UI thread handles scrolling. When too many components render at once, frames are dropped.

`FlatList` is React Native's virtualized list component. It only renders items visible on screen (plus a buffer), unmounting items that scroll off-screen. This is the right tool for any list longer than a few dozen items.

## The basic setup

```javascript
<FlatList
  data={items}
  keyExtractor={item => item.id.toString()}
  renderItem={({ item }) => <ItemComponent item={item} />}
/>
```

This works. But several props significantly affect performance.

## getItemLayout: skip layout measurement

By default, FlatList measures the height of each item as it renders. For variable-height items, this is necessary. For fixed-height items, it's wasted work.

If every item has the same height, provide `getItemLayout`:

```javascript
const ITEM_HEIGHT = 72;

<FlatList
  data={items}
  getItemLayout={(data, index) => ({
    length: ITEM_HEIGHT,
    offset: ITEM_HEIGHT * index,
    index,
  })}
  renderItem={({ item }) => <ItemComponent item={item} />}
/>
```

With `getItemLayout`, FlatList can calculate scroll positions instantly and jump to any item without rendering everything in between. `scrollToIndex` works correctly only with `getItemLayout`.

## keyExtractor: stable keys

```javascript
keyExtractor={item => item.id.toString()}
```

Keys must be strings. Using the item's unique ID ensures React can reconcile the list correctly when items are reordered or updated. Without stable keys, items unmount and remount unnecessarily.

## initialNumToRender

How many items to render on the first paint. Defaults to 10.

```javascript
initialNumToRender={8}
```

Reduce this to speed up the initial render. Only render what fits on screen. Increasing it delays the first paint without benefit.

## maxToRenderPerBatch

How many items to render per batch (each batch is one frame). Defaults to 10.

```javascript
maxToRenderPerBatch={5}
```

Reducing this makes each frame cheaper at the cost of a brief "blank" appearance when scrolling very fast. Increasing it renders more per frame, which can cause jank. The default is usually fine.

## windowSize

The rendering window size as a multiple of the viewport height. Items within this window are rendered; items outside are unmounted. Defaults to 21 (10 viewports above, 10 below).

```javascript
windowSize={10}
```

Reducing this saves memory but causes more "blank" flashes during fast scrolling. For long lists with complex items, reducing to 5-10 is often a net win.

## removeClippedSubviews

On Android, `removeClippedSubviews` detaches off-screen views from the view hierarchy, reducing memory usage:

```javascript
removeClippedSubviews={Platform.OS === 'android'}
```

This is experimental on iOS and can cause rendering issues. Apply it only on Android.

## Memoizing the renderItem component

The most impactful optimization is ensuring the `renderItem` component doesn't re-render unnecessarily:

```javascript
// Without memoization: re-renders on every FlatList render
const renderItem = ({ item }) => <ItemComponent item={item} />;

// With memoization: re-renders only when item changes
const ItemComponent = React.memo(function ItemComponent({ item }) {
  return (
    <View style={styles.item}>
      <Text>{item.title}</Text>
    </View>
  );
});

// Pass a stable reference
<FlatList
  data={items}
  renderItem={({ item }) => <ItemComponent item={item} />}
/>
```

Also define `renderItem` outside the render function or wrap it in `useCallback` so the reference doesn't change on every render:

```javascript
const renderItem = useCallback(
  ({ item }) => <ItemComponent item={item} />,
  [] // stable, assuming ItemComponent is memoized
);
```

## A practical configuration

For a typical social feed with fixed-height cards:

```javascript
<FlatList
  data={posts}
  keyExtractor={item => item.id}
  renderItem={renderItem}
  getItemLayout={(_, index) => ({
    length: POST_HEIGHT,
    offset: POST_HEIGHT * index,
    index,
  })}
  initialNumToRender={8}
  maxToRenderPerBatch={5}
  windowSize={10}
  removeClippedSubviews={Platform.OS === 'android'}
  showsVerticalScrollIndicator={false}
/>
```

Profile before optimizing -- React DevTools' profiler shows exactly which components are rendering and how long they take.
