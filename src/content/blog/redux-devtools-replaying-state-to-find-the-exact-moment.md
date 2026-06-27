---
title: "Redux DevTools: replaying state to find the exact moment things broke."
description: "A practical guide to Redux DevTools features -- time-travel debugging, action inspection, and state diffing -- that make tracking down state bugs much faster."
pubDate: 2025-01-09
tags: ["Redux", "Debugging"]
draft: false
---

## Why Redux state is debuggable by design

Redux enforces that state changes happen only through dispatched actions, and each action produces a completely new state object. This means the history of your application state is a sequence of (action, state) pairs that can be recorded and replayed. Redux DevTools exploits exactly this property.

## Installing and connecting

Redux Toolkit configures the DevTools extension automatically in development. Install the browser extension (available for Chrome and Firefox), then open any app using Redux:

```javascript
// configureStore already includes devTools in development
import { configureStore } from '@reduxjs/toolkit';

export const store = configureStore({
  reducer: rootReducer,
  // devTools: true is the default in development
});
```

Once the extension detects a store, the Redux tab appears in browser DevTools.

## The action log

The left panel lists every dispatched action in order. Each entry shows the action type and a timestamp. Clicking an action shows three tabs:

- **Action**: the full action object, including payload
- **State**: the complete Redux state after that action was applied
- **Diff**: what changed between the previous state and this state

The diff view is the fastest way to confirm whether a reducer is doing what you expect. If you dispatch `cart/itemAdded` and the diff shows no change to `cart.items`, the reducer is not handling that action.

## Time-travel debugging

Clicking any action in the list "jumps" the application to that point in history. The UI re-renders to reflect the state at that exact moment. This lets you reproduce bugs that depend on a specific sequence of actions without manually repeating the steps each time.

The slider at the bottom lets you scrub through the action history continuously. Watching the UI change as you drag the slider reveals which action caused a layout break, a wrong count, or a disappeared element.

## Skipping actions

Each action in the list has a checkbox. Unchecking an action removes it from the replay, as if it was never dispatched. This is useful for testing: "what if this action had not fired?" The state is recomputed as if the unchecked actions never happened.

## Exporting and importing state

The DevTools panel has an export button that saves the current action log as a JSON file. You can share this file with a teammate who imports it into their DevTools and sees the exact same sequence of actions replaying in their browser.

This is the practical version of "it works on my machine." Instead of describing the reproduction steps, you hand someone the exact state history.

## Dispatching actions manually

The DevTools has a dispatcher panel where you can type a raw action and dispatch it:

```json
{
  "type": "cart/itemAdded",
  "payload": { "id": 42, "name": "Widget", "price": 9.99, "qty": 1 }
}
```

This is useful for testing reducers without building a UI flow. You can verify that a specific action produces the state you expect without clicking through forms.

## The "commit" button

As you interact with an app, the action log grows. Pressing "Commit" collapses the current state into a base snapshot and clears the action list. Subsequent actions are logged relative to that snapshot. This keeps the DevTools usable in long sessions without an overwhelming action list.

## Practical workflow

When a bug is reported ("the cart total is wrong after removing an item"), a good debugging flow with DevTools looks like this:

1. Reproduce the steps in the app
2. Look at the action log -- find `cart/itemRemoved`
3. Click that action and open the Diff tab
4. Verify the state after removal matches expectations
5. If the diff shows the item is still in `entities`, the reducer has a bug
6. If the diff looks correct but the UI is wrong, the bug is in a selector or component

DevTools eliminates the guesswork about whether state changed correctly. Either the diff shows the right change or it doesn't. That binary answer cuts debugging time considerably.
