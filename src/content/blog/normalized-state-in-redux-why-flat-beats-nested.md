---
title: "Normalized state in Redux: why flat beats nested."
description: "Nested arrays in Redux state cause duplication and painful updates. Normalization flattens the structure so updates are simple and lookups are O(1)."
pubDate: 2025-01-06
tags: ["Redux"]
draft: false
---

## The nested state problem

When you fetch a list of posts with their comments, the tempting structure mirrors the API response:

```javascript
{
  posts: [
    {
      id: 1,
      title: "First post",
      comments: [
        { id: 101, text: "Nice post", authorId: 5 },
        { id: 102, text: "Thanks!", authorId: 1 },
      ]
    },
    {
      id: 2,
      title: "Second post",
      comments: [
        { id: 103, text: "Interesting", authorId: 5 },
      ]
    }
  ]
}
```

This works until you need to update comment 101. You have to find the right post in the array, find the right comment in that post's array, and produce a new array at every level -- all while keeping immutability intact. If the same author appears across hundreds of comments, any author update touches every occurrence.

## Normalized structure

Normalization flattens the data into lookup tables keyed by ID:

```javascript
{
  posts: {
    ids: [1, 2],
    entities: {
      1: { id: 1, title: "First post", commentIds: [101, 102] },
      2: { id: 2, title: "Second post", commentIds: [103] },
    }
  },
  comments: {
    ids: [101, 102, 103],
    entities: {
      101: { id: 101, text: "Nice post", authorId: 5 },
      102: { id: 102, text: "Thanks!", authorId: 1 },
      103: { id: 103, text: "Interesting", authorId: 5 },
    }
  }
}
```

Now updating comment 101 is a single operation:

```javascript
state.comments.entities[101].text = "Nice post, updated";
```

No searching, no nested array traversal. The update is O(1).

## createEntityAdapter

Redux Toolkit ships `createEntityAdapter`, which sets up this structure automatically and provides CRUD operations for free.

```javascript
import { createSlice, createEntityAdapter } from '@reduxjs/toolkit';

const commentsAdapter = createEntityAdapter();

const initialState = commentsAdapter.getInitialState();
// { ids: [], entities: {} }

const commentsSlice = createSlice({
  name: 'comments',
  initialState,
  reducers: {
    commentAdded: commentsAdapter.addOne,
    commentUpdated: commentsAdapter.updateOne,
    commentRemoved: commentsAdapter.removeOne,
    commentsReceived(state, action) {
      commentsAdapter.setAll(state, action.payload);
    },
  },
});
```

`addOne`, `updateOne`, `removeOne`, `setAll`, `upsertMany` -- these handle the mutations correctly without you writing array manipulation logic.

## The adapter's selectors

`createEntityAdapter` also generates selectors:

```javascript
export const {
  selectAll: selectAllComments,
  selectById: selectCommentById,
  selectIds: selectCommentIds,
} = commentsAdapter.getSelectors(state => state.comments);
```

`selectAll` returns an ordered array using the `ids` list. `selectById` does an O(1) lookup in `entities`. These compose with Reselect when you need derived data.

## Rendering normalized data

To render a post's comments in order, you store the IDs on the post and look up each comment:

```javascript
function PostComments({ postId }) {
  const post = useSelector(state => selectPostById(state, postId));
  const comments = useSelector(state =>
    post.commentIds.map(id => selectCommentById(state, id))
  );

  return (
    <ul>
      {comments.map(c => <li key={c.id}>{c.text}</li>)}
    </ul>
  );
}
```

Or use `createSelector` to memoize the mapped array so it doesn't re-create on every render:

```javascript
const makeSelectPostComments = postId =>
  createSelector(
    [state => selectPostById(state, postId), state => state.comments.entities],
    (post, commentEntities) =>
      post.commentIds.map(id => commentEntities[id])
  );
```

## When normalization is overkill

For small, read-only datasets that are never updated client-side, normalization adds structure without benefit. If you fetch a list of countries once and display it, a plain array is fine. Normalization pays off when:

- Data is updated frequently
- The same entity appears in multiple places
- You need O(1) lookup by ID
- You are managing relationships between entities

The rule of thumb: if your reducer has logic that traverses an array to find an item before updating it, that slice should probably be normalized.
