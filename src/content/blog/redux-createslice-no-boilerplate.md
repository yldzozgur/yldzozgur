---
title: "Redux without the boilerplate: what createSlice actually removes."
description: "How createSlice from Redux Toolkit eliminates the action types, action creators, and switch statements that made classic Redux painful to maintain."
pubDate: 2024-12-23
tags: ["Redux Toolkit"]
draft: false
---

Classic Redux requires three separate pieces for every feature: action type constants, action creator functions, and a reducer with a switch statement. For a simple counter, that's thirty lines of boilerplate before you write any business logic. `createSlice` from Redux Toolkit collapses all three into one declaration.

## What classic Redux looks like

```js
// 1. Action type constants
const INCREMENT = 'counter/increment';
const DECREMENT = 'counter/decrement';
const RESET = 'counter/reset';

// 2. Action creators
function increment() { return { type: INCREMENT }; }
function decrement() { return { type: DECREMENT }; }
function reset() { return { type: RESET }; }

// 3. Reducer
function counterReducer(state = { value: 0 }, action) {
  switch (action.type) {
    case INCREMENT:
      return { ...state, value: state.value + 1 };
    case DECREMENT:
      return { ...state, value: state.value - 1 };
    case RESET:
      return { ...state, value: 0 };
    default:
      return state;
  }
}

export { increment, decrement, reset, counterReducer };
```

Every new action requires touching three separate sections. Typos in action type strings cause silent failures. Spread operators in every case to avoid mutation.

## The createSlice version

```js
import { createSlice } from '@reduxjs/toolkit';

const counterSlice = createSlice({
  name: 'counter',
  initialState: { value: 0 },
  reducers: {
    increment(state) {
      state.value += 1; // Direct mutation is safe here (Immer handles it)
    },
    decrement(state) {
      state.value -= 1;
    },
    reset(state) {
      state.value = 0;
    },
    incrementByAmount(state, action) {
      state.value += action.payload;
    },
  },
});

export const { increment, decrement, reset, incrementByAmount } = counterSlice.actions;
export default counterSlice.reducer;
```

`createSlice` generates action type strings (`counter/increment`, `counter/decrement`) automatically from the slice name and reducer key. It generates action creators that match those types. It wraps the reducer in Immer so you can write mutations directly.

## What Immer does

Immer is the library that makes direct state mutation safe in `createSlice` reducers. When you write `state.value += 1`, you are not actually mutating the Redux state. Immer intercepts the mutation, builds a new immutable state object from your changes, and returns that.

This means the spread-heavy update patterns from classic Redux become unnecessary:

```js
// Classic Redux: required spread to avoid mutation
case ADD_TODO:
  return {
    ...state,
    todos: [...state.todos, action.payload],
    lastUpdated: Date.now(),
  };

// createSlice with Immer: direct push and assignment
addTodo(state, action) {
  state.todos.push(action.payload);
  state.lastUpdated = Date.now();
}
```

The second version is both shorter and easier to read. Immer ensures immutability under the hood.

## Setting up the store

```js
import { configureStore } from '@reduxjs/toolkit';
import counterReducer from './counterSlice';
import todosReducer from './todosSlice';

export const store = configureStore({
  reducer: {
    counter: counterReducer,
    todos: todosReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

`configureStore` also sets up Redux DevTools Extension automatically and includes the `redux-thunk` middleware by default.

## Using the slice in components

```jsx
import { useSelector, useDispatch } from 'react-redux';
import { increment, decrement, incrementByAmount } from './counterSlice';

function Counter() {
  const count = useSelector(state => state.counter.value);
  const dispatch = useDispatch();

  return (
    <div>
      <p>{count}</p>
      <button onClick={() => dispatch(increment())}>+</button>
      <button onClick={() => dispatch(decrement())}>-</button>
      <button onClick={() => dispatch(incrementByAmount(5))}>+5</button>
    </div>
  );
}
```

`incrementByAmount(5)` creates the action `{ type: 'counter/incrementByAmount', payload: 5 }`. The `payload` key is the convention: single-argument action creators put their argument in `payload` automatically.

## Handling more complex state with reducers

```js
const todosSlice = createSlice({
  name: 'todos',
  initialState: {
    items: [],
    filter: 'all',
  },
  reducers: {
    addTodo(state, action) {
      state.items.push({
        id: Date.now(),
        text: action.payload,
        completed: false,
      });
    },
    toggleTodo(state, action) {
      const todo = state.items.find(item => item.id === action.payload);
      if (todo) {
        todo.completed = !todo.completed;
      }
    },
    removeTodo(state, action) {
      state.items = state.items.filter(item => item.id !== action.payload);
    },
    setFilter(state, action) {
      state.filter = action.payload;
    },
  },
});
```

Finding an item and mutating it directly (`todo.completed = !todo.completed`) would break classic Redux. With Immer inside `createSlice`, it works correctly.

## The prepare callback for custom action shapes

When you need more control over the action's payload (adding an ID, a timestamp, or transforming the input), use the `prepare` callback:

```js
const postsSlice = createSlice({
  name: 'posts',
  initialState: [],
  reducers: {
    addPost: {
      reducer(state, action) {
        state.push(action.payload);
      },
      prepare(title, content) {
        return {
          payload: {
            id: crypto.randomUUID(),
            title,
            content,
            createdAt: new Date().toISOString(),
          },
        };
      },
    },
  },
});

// Usage: dispatch(addPost('Title', 'Content'))
// Action: { type: 'posts/addPost', payload: { id: '...', title: 'Title', ... } }
```

The `prepare` function runs before the reducer and shapes the payload. The reducer receives the transformed payload.

`createSlice` does not change what Redux does. It changes how much code you write to do it.
