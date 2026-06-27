---
title: "Redux thunks: async logic without an extra library."
description: "How createAsyncThunk from Redux Toolkit handles async operations like API calls, manages loading and error states automatically, and integrates with extraReducers."
pubDate: 2024-12-26
tags: ["Redux Toolkit"]
draft: false
---

Redux reducers are synchronous and pure. They receive state and an action, return new state. No API calls, no timers, no side effects. Thunks are the mechanism for putting async logic into Redux without breaking these rules.

Redux Toolkit ships with `createAsyncThunk`, which handles the most common async pattern: fetch data, track loading state, handle errors. You don't need redux-saga or redux-observable for the typical CRUD operation.

## What a thunk is

A thunk is a function that returns another function. Instead of dispatching a plain action object, you dispatch a function. Redux's thunk middleware checks if the dispatched value is a function. If it is, it calls that function with `dispatch` and `getState`. If it's a plain object, it passes it to the reducer normally.

```js
// A plain action
dispatch({ type: 'counter/increment' });

// A thunk: dispatching a function
dispatch((dispatch, getState) => {
  const state = getState();
  if (state.counter.value < 10) {
    dispatch({ type: 'counter/increment' });
  }
});
```

This is the foundation. `createAsyncThunk` builds on it.

## createAsyncThunk

`createAsyncThunk` takes an action type prefix and an async payload creator function. It automatically dispatches three actions: `pending`, `fulfilled`, and `rejected`.

```js
import { createAsyncThunk } from '@reduxjs/toolkit';

export const fetchUser = createAsyncThunk(
  'users/fetchById',
  async (userId) => {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch user');
    }
    return response.json(); // The returned value becomes action.payload in fulfilled
  }
);
```

When you `dispatch(fetchUser(42))`:

1. `users/fetchById/pending` is dispatched immediately
2. The async function runs
3. If it resolves: `users/fetchById/fulfilled` is dispatched with the return value as `payload`
4. If it throws: `users/fetchById/rejected` is dispatched with the error

## Handling the three states in a slice

Use `extraReducers` to respond to actions from outside the slice, including those created by `createAsyncThunk`:

```js
import { createSlice } from '@reduxjs/toolkit';
import { fetchUser } from './userThunks';

const userSlice = createSlice({
  name: 'user',
  initialState: {
    data: null,
    status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
    error: null,
  },
  reducers: {},
  extraReducers(builder) {
    builder
      .addCase(fetchUser.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.data = action.payload;
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      });
  },
});

export default userSlice.reducer;
```

The `builder` pattern provides autocompletion and type safety. Each `.addCase` handles one action type.

## Using the thunk in a component

```jsx
import { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchUser } from './userThunks';

function UserProfile({ userId }) {
  const dispatch = useDispatch();
  const { data: user, status, error } = useSelector(state => state.user);

  useEffect(() => {
    dispatch(fetchUser(userId));
  }, [dispatch, userId]);

  if (status === 'loading') return <Spinner />;
  if (status === 'failed') return <p>Error: {error}</p>;
  if (!user) return null;

  return <div>{user.name}</div>;
}
```

The status field drives the UI. No local loading or error state needed in the component.

## Passing arguments and accessing state

The payload creator receives two arguments: the value you pass to the dispatched thunk, and a `thunkAPI` object:

```js
export const createPost = createAsyncThunk(
  'posts/create',
  async (postData, { getState, dispatch, rejectWithValue }) => {
    const state = getState();
    const token = state.auth.token;

    try {
      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(postData),
      });

      if (!response.ok) {
        const error = await response.json();
        return rejectWithValue(error); // Custom error payload
      }

      return response.json();
    } catch (err) {
      return rejectWithValue({ message: 'Network error' });
    }
  }
);
```

`rejectWithValue` lets you control what goes into `action.payload` on rejection (instead of the thrown error going into `action.error`). This is useful when the server returns structured error information you want to display.

## Checking the result in a component

`dispatch` with a thunk returns a promise. You can `await` it and inspect the result:

```jsx
async function handleSubmit(formData) {
  const result = await dispatch(createPost(formData));

  if (createPost.fulfilled.match(result)) {
    navigate(`/posts/${result.payload.id}`);
  } else {
    showError(result.payload?.message || 'Failed to create post');
  }
}
```

`createPost.fulfilled.match(result)` is a type-safe way to check whether the thunk succeeded.

## When you don't need createAsyncThunk

For simple cases where you want async logic without the automatic pending/fulfilled/rejected states, write a plain thunk:

```js
export const logAndIncrement = () => async (dispatch, getState) => {
  const currentCount = getState().counter.value;
  await logAnalytics('increment', { from: currentCount });
  dispatch(increment());
};
```

Dispatch it like any other action: `dispatch(logAndIncrement())`. Plain thunks work for side effects that don't need to track loading state in the store.

`createAsyncThunk` is the right tool when you need the UI to reflect loading, success, and error states. Plain thunks work for everything else.
