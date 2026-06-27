---
title: "Optimistic UI: updating the screen before the server responds."
description: "How optimistic UI works, how to implement it in React, and how to roll back cleanly when the server request fails."
pubDate: 2024-12-12
tags: ["React"]
draft: false
---

Optimistic UI is the pattern where you update the interface immediately when a user takes an action, before waiting for the server to confirm the change. If the server succeeds, nothing more is needed. If the server fails, you roll back the UI to its previous state and show an error.

The name comes from the assumption: you assume the operation will succeed, apply the change optimistically, and handle failure as the exception rather than the rule.

## Why it matters

The alternative is pessimistic UI: the user clicks "like," the button does nothing visible, a spinner appears for 200-500ms, then the like count increments. For frequent, low-stakes actions, this latency is noticeable and makes the app feel slow even on fast networks.

With optimistic UI, the like count increments immediately. The network request runs in the background. For the majority of successful requests, the user never perceives any delay.

## A basic implementation

```jsx
function LikeButton({ postId, initialLikeCount, initialIsLiked }) {
  const [isLiked, setIsLiked] = useState(initialIsLiked);
  const [likeCount, setLikeCount] = useState(initialLikeCount);

  async function handleClick() {
    // Optimistic update
    const previousIsLiked = isLiked;
    const previousLikeCount = likeCount;
    setIsLiked(!isLiked);
    setLikeCount(isLiked ? likeCount - 1 : likeCount + 1);

    // Server request
    try {
      await toggleLike(postId);
    } catch (error) {
      // Rollback on failure
      setIsLiked(previousIsLiked);
      setLikeCount(previousLikeCount);
      showToast('Could not update like. Please try again.');
    }
  }

  return (
    <button onClick={handleClick} className={isLiked ? 'liked' : ''}>
      {isLiked ? 'Unlike' : 'Like'} ({likeCount})
    </button>
  );
}
```

The key steps: save the previous values before updating, apply the optimistic update, catch failures and restore the saved values.

## Optimistic list updates

Adding an item to a list optimistically requires a temporary item with a local ID:

```jsx
function TodoList() {
  const [todos, setTodos] = useState([]);
  const [newTodo, setNewTodo] = useState('');

  async function handleAdd() {
    const text = newTodo;
    setNewTodo('');

    // Create temporary item with local ID
    const tempId = `temp-${Date.now()}`;
    const optimisticTodo = { id: tempId, text, isPending: true };

    // Optimistic update
    setTodos(prev => [...prev, optimisticTodo]);

    try {
      const savedTodo = await createTodo({ text });
      // Replace temporary item with server response (real ID)
      setTodos(prev =>
        prev.map(todo => todo.id === tempId ? savedTodo : todo)
      );
    } catch (error) {
      // Remove the optimistic item
      setTodos(prev => prev.filter(todo => todo.id !== tempId));
      setNewTodo(text); // Restore the input
      showToast('Failed to add todo. Please try again.');
    }
  }

  return (
    <ul>
      {todos.map(todo => (
        <li key={todo.id} style={{ opacity: todo.isPending ? 0.6 : 1 }}>
          {todo.text}
          {todo.isPending && <span> (saving...)</span>}
        </li>
      ))}
    </ul>
  );
}
```

The visual hint (`opacity: 0.6`) signals to the user that the item is still being saved. This is optional but helpful for slower connections.

## Using React's useOptimistic hook (React 19+)

React 19 introduced `useOptimistic` specifically for this pattern:

```jsx
import { useOptimistic, useState, useTransition } from 'react';

function LikeButton({ postId, initialCount }) {
  const [count, setCount] = useState(initialCount);
  const [optimisticCount, addOptimistic] = useOptimistic(
    count,
    (current, delta) => current + delta
  );
  const [isPending, startTransition] = useTransition();

  async function handleClick() {
    startTransition(async () => {
      addOptimistic(1);
      const newCount = await toggleLike(postId);
      setCount(newCount);
    });
  }

  return (
    <button onClick={handleClick}>
      {optimisticCount} likes
    </button>
  );
}
```

`useOptimistic` manages the temporary state automatically. When the async transition completes, it reverts to the real value returned from the server.

## Handling concurrent actions

A user might click like, then unlike, before either request completes. Without care, the responses can arrive out of order and leave the UI in an inconsistent state.

A simple solution: track the latest request and ignore responses from earlier ones:

```jsx
const latestRequestId = useRef(0);

async function handleClick() {
  const requestId = ++latestRequestId.current;
  const previous = { isLiked, likeCount };

  setIsLiked(!isLiked);
  setLikeCount(isLiked ? likeCount - 1 : likeCount + 1);

  try {
    await toggleLike(postId);
    // Only update if this is still the latest request
    if (latestRequestId.current !== requestId) return;
  } catch (error) {
    if (latestRequestId.current !== requestId) return;
    setIsLiked(previous.isLiked);
    setLikeCount(previous.likeCount);
  }
}
```

## When not to use optimistic UI

Optimistic updates work best for actions that almost always succeed. Avoid them for:

- **Destructive actions** (deleting an account, canceling a subscription). Show a confirmation and wait for server confirmation before updating UI.
- **Financial transactions**. Users expect confirmation before considering a payment complete.
- **Actions with complex server-side logic** where the server result may legitimately differ from the expected client-side result.

For the common cases (likes, follows, cart additions, task completion), optimistic UI dramatically improves perceived performance with relatively little additional code.
