---
title: "Flexbox on mobile: the defaults that differ from the web."
description: "React Native uses Flexbox for layout, but the defaults are different from the web. The key differences that cause layout confusion and how to work with them."
pubDate: 2025-01-30
tags: ["React-Native", "Mobile", "CSS"]
draft: false
---

## Same model, different defaults

React Native's layout engine is based on Flexbox, and the properties are mostly the same as CSS Flexbox. But several defaults are different, and those differences cause most of the layout confusion for developers coming from the web.

## flexDirection defaults to column

On the web, `flex-direction` defaults to `row` -- flex children line up horizontally. In React Native, `flexDirection` defaults to `column` -- children stack vertically.

```javascript
// Web CSS
// .container { display: flex; }
// Children go left to right by default

// React Native
const styles = StyleSheet.create({
  container: {
    flex: 1,
    // flexDirection is 'column' by default
    // Children stack top to bottom
  },
  row: {
    flexDirection: 'row', // explicit to go horizontal
  },
});
```

This is intentional -- most mobile screens are vertically scrolling, single-column layouts. But it means any web developer's instinct about flex direction will be wrong until re-learned.

## alignContent defaults to flex-start

On the web, `align-content` defaults to `stretch`. In React Native it defaults to `flex-start`. This affects multi-line flex containers (when `flexWrap: 'wrap'` is enabled). Lines do not stretch to fill the container height automatically.

## flex takes a single number

CSS `flex` is a shorthand for `flex-grow`, `flex-shrink`, and `flex-basis`. React Native's `flex` is simpler: it takes a single positive number that distributes space proportionally.

```javascript
const styles = StyleSheet.create({
  container: {
    flex: 1, // takes all available space
    flexDirection: 'row',
  },
  left: {
    flex: 1, // takes 1/3 of available space
  },
  right: {
    flex: 2, // takes 2/3 of available space
  },
});
```

`flex: 1` on the root container is the React Native equivalent of `height: 100vh` on the web -- it tells the component to fill all available space. Without it, a component only takes as much space as its content requires.

## No automatic overflow

On the web, content that exceeds its container overflows and can be scrolled. In React Native, overflow is hidden by default and there is no automatic scroll. If you want scrollable content, you explicitly use `<ScrollView>` or `<FlatList>`.

This changes how you think about screen layout:

```javascript
function Screen() {
  return (
    <View style={{ flex: 1 }}>
      {/* Fixed header */}
      <View style={{ height: 60, backgroundColor: '#333' }} />

      {/* Scrollable content */}
      <ScrollView style={{ flex: 1 }}>
        {items.map(item => <Item key={item.id} {...item} />)}
      </ScrollView>

      {/* Fixed footer */}
      <View style={{ height: 80, backgroundColor: '#f0f0f0' }} />
    </View>
  );
}
```

The `ScrollView` gets `flex: 1` to fill the remaining space between the fixed header and footer.

## position is relative by default

Same as the web, but worth noting: `position: 'absolute'` positions an element relative to its nearest positioned ancestor (any element with `position: 'absolute'` or `position: 'relative'`). There is no `position: 'fixed'` -- truly fixed elements on screen require a different approach, usually via the navigation library or a modal overlay.

## gap support

`gap`, `rowGap`, and `columnGap` work in React Native as of React Native 0.71. Before that version, you had to use margins to space flex children. If you're maintaining an older codebase you may still see margin-based spacing:

```javascript
// Old approach
const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
  },
  item: {
    marginRight: 8, // spacing between items
  },
});

// Modern approach
const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 8,
  },
});
```

## Practical layout template

A common screen layout that accounts for all of this:

```javascript
const styles = StyleSheet.create({
  screen: {
    flex: 1,           // fill the device screen
    backgroundColor: '#fff',
  },
  content: {
    flex: 1,           // fill remaining space
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
});
```

Once the column-first default is internalized, React Native Flexbox becomes intuitive. The mental model is building a vertical stack of blocks, with rows as an explicit override.

