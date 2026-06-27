---
title: "Virtualizing long lists: rendering 10,000 rows without freezing the browser."
description: "How virtualization works, how to implement it with react-window or TanStack Virtual, and what to consider when your list has variable-height items."
pubDate: 2024-12-19
tags: ["React"]
draft: false
---

Rendering 10,000 rows in React creates 10,000 DOM nodes. Browsers can handle creating them, but the performance cost shows up in scrolling jank, slow initial renders, and high memory usage. Virtualization solves this by only rendering the rows currently visible in the viewport, plus a small buffer. The rest of the rows are not in the DOM at all.

## How virtualization works

The technique is called "windowing." Imagine the list as a large fixed-height container. Inside it, only the visible "window" of items is rendered. As the user scrolls, items at the top are removed from the DOM and new items are added at the bottom (and vice versa). The total number of DOM nodes stays constant regardless of how many items are in the list.

The container needs a fixed height so the browser knows how tall the scrollable area is, even though most of the items aren't in the DOM yet. The virtualization library computes item positions mathematically and uses absolute positioning or transform to place them correctly.

## react-window: the standard library

`react-window` by Brian Vaughn is small, fast, and well-maintained.

```bash
npm install react-window
```

**Fixed-height rows:**

```jsx
import { FixedSizeList } from 'react-window';

const ITEM_HEIGHT = 50;
const VISIBLE_HEIGHT = 500;

function Row({ index, style }) {
  return (
    <div style={style}>
      Item {index}
    </div>
  );
}

function VirtualList({ items }) {
  return (
    <FixedSizeList
      height={VISIBLE_HEIGHT}
      itemCount={items.length}
      itemSize={ITEM_HEIGHT}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          {items[index].name}
        </div>
      )}
    </FixedSizeList>
  );
}
```

The `style` prop from the render callback must be applied to the outer element of each row. It contains the `position`, `top`, `height`, and `width` that position the row correctly in the virtual list. Do not omit it.

**Variable-height rows:**

When row heights differ (messages of varying length, cards with different content), use `VariableSizeList`:

```jsx
import { VariableSizeList } from 'react-window';

const itemHeights = [60, 80, 120, 40, 90]; // Heights can come from measurement

function getItemSize(index) {
  return itemHeights[index] || 60;
}

function VariableList({ items }) {
  return (
    <VariableSizeList
      height={500}
      itemCount={items.length}
      itemSize={getItemSize}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          {items[index].content}
        </div>
      )}
    </VariableSizeList>
  );
}
```

`VariableSizeList` requires knowing heights upfront. If you can't know heights before rendering, you need to measure items on first render and use those measurements.

## Passing data to rows

Row renderers receive `index` and `style`. To pass list data, use `itemData`:

```jsx
function Row({ data, index, style }) {
  const item = data.items[index];
  return (
    <div style={style} onClick={() => data.onSelect(item)}>
      {item.name}
    </div>
  );
}

function VirtualList({ items, onSelect }) {
  const itemData = useMemo(() => ({ items, onSelect }), [items, onSelect]);

  return (
    <FixedSizeList
      height={500}
      itemCount={items.length}
      itemSize={50}
      width="100%"
      itemData={itemData}
    >
      {Row}
    </FixedSizeList>
  );
}
```

The `useMemo` is important here. If `itemData` is created inline, it changes reference on every render, which prevents `React.memo` from working on the row component.

## TanStack Virtual: more control

For complex cases (dynamic heights, bi-directional infinite scroll, table grids), `@tanstack/react-virtual` provides a lower-level API with more flexibility:

```bash
npm install @tanstack/react-virtual
```

```jsx
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }) {
  const parentRef = useRef(null);

  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div
      ref={parentRef}
      style={{ height: '500px', overflow: 'auto' }}
    >
      <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
        {rowVirtualizer.getVirtualItems().map(virtualItem => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {items[virtualItem.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

The inner `div` has the total calculated height of all items, which creates the scrollbar. Only the virtual items (currently visible rows) are rendered as absolute-positioned children.

## Dynamic heights with measurement

When you can't know heights in advance, measure after render:

```jsx
const rowVirtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 80, // Starting estimate
  measureElement: (element) => element?.getBoundingClientRect().height,
});

// In the row:
<div
  ref={rowVirtualizer.measureElement}
  data-index={virtualItem.index}
>
  {items[virtualItem.index].content}
</div>
```

The virtualizer measures each row as it renders and recalculates positions with the real heights. The first render uses estimates, subsequent renders use measured values.

## What virtualization doesn't help with

Virtualization helps when the bottleneck is the number of DOM nodes. It doesn't help when:

- Individual items are themselves expensive to render (each item runs a heavy computation). Memoize expensive items with `React.memo`.
- The list items need to be in the DOM for accessibility features like `find in page` to work.
- You need to scroll to an item by its content (text search). Only rendered items are searchable.

For most data tables, infinite scroll feeds, and option lists with thousands of entries, virtualization is the right tool.
