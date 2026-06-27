---
title: "You're using async/await without knowing what it hides."
description: "async/await is syntactic sugar over Promises. Understanding what it compiles to explains every confusing behavior."
pubDate: 2024-01-04
tags: ["JavaScript"]
draft: false
---

`async/await` made asynchronous JavaScript readable. It also made it easy to write code that looks synchronous but has asynchronous footguns hidden inside. Most of those footguns come from not knowing what `async/await` actually compiles to.

## What async/await really is

An `async` function always returns a Promise, even if you return a plain value:

```js
async function getNumber() {
  return 42;
}

getNumber(); // Promise { 42 }
getNumber().then(console.log); // 42
```

`await` suspends the execution of the async function and resumes it when the awaited Promise settles. It does not block the thread. The event loop is free to process other work while your function is suspended.

Under the hood, this:

```js
async function fetchUser(id) {
  const user = await getUser(id);
  return user.name;
}
```

Is roughly equivalent to:

```js
function fetchUser(id) {
  return getUser(id).then(user => user.name);
}
```

## The sequential trap

The most common mistake is awaiting things that could run concurrently:

```js
// This takes ~2 seconds if each call takes ~1 second
async function loadDashboard(userId) {
  const user = await fetchUser(userId);
  const posts = await fetchPosts(userId);
  const notifications = await fetchNotifications(userId);
  return { user, posts, notifications };
}
```

Each `await` waits for the previous one to finish before starting the next. If these three fetches are independent, you are serializing work that does not need to be serial.

Fix it with `Promise.all`:

```js
async function loadDashboard(userId) {
  const [user, posts, notifications] = await Promise.all([
    fetchUser(userId),
    fetchPosts(userId),
    fetchNotifications(userId),
  ]);
  return { user, posts, notifications };
}
```

Now all three requests fire at the same time. Total time is the duration of the slowest one, not the sum of all three.

## Error handling: try/catch vs .catch()

Both work, but they have different shapes:

```js
// try/catch
async function load() {
  try {
    const data = await fetch("/api/data").then(r => r.json());
    return data;
  } catch (err) {
    console.error(err);
    return null;
  }
}

// .catch() attached to the awaited expression
async function load() {
  const data = await fetch("/api/data")
    .then(r => r.json())
    .catch(() => null);
  return data;
}
```

The `.catch()` style is useful when you want a default value for a single operation without a full try/catch block. Use try/catch when you want to handle errors from a block of statements together.

One subtle thing: if you forget `await` on a rejected Promise inside a try/catch, the catch will not fire:

```js
async function broken() {
  try {
    const p = fetchSomething(); // no await
    return p; // the rejection propagates after this function returns
  } catch (err) {
    // this never runs
  }
}
```

## Unhandled promise rejections

In Node.js, an unhandled rejection will crash your process (since Node 15). In the browser it fires the `unhandledrejection` event. This happens when you call an async function but do not attach `.catch()` or `await` it:

```js
// Fire and forget — if this rejects, the rejection is unhandled
sendAnalytics(event);

// Safe fire and forget
sendAnalytics(event).catch(err => {
  // log but don't crash
  console.error("analytics failed:", err);
});
```

## async/await in loops

`forEach` does not await async callbacks:

```js
// This does NOT wait for each async operation
users.forEach(async (user) => {
  await sendEmail(user.email); // each iteration starts but nothing awaits it
});
console.log("done"); // runs immediately, before any emails are sent
```

For sequential async work over an array, use `for...of`:

```js
for (const user of users) {
  await sendEmail(user.email); // each email waits for the previous
}
```

For concurrent async work, use `Promise.all` with `map`:

```js
await Promise.all(users.map(user => sendEmail(user.email)));
```

## What async does to return values

A function marked `async` that throws will produce a rejected Promise:

```js
async function fail() {
  throw new Error("oops");
}

fail(); // Promise { <rejected> Error: oops }
```

This is important in Express middleware. If an async route handler throws, Express will not automatically catch it (in Express 4; Express 5 handles this):

```js
// Express 4: unhandled rejection if getUser throws
app.get("/user/:id", async (req, res) => {
  const user = await getUser(req.params.id);
  res.json(user);
});

// Safe version
app.get("/user/:id", async (req, res, next) => {
  try {
    const user = await getUser(req.params.id);
    res.json(user);
  } catch (err) {
    next(err);
  }
});
```

## Promise.allSettled vs Promise.all

`Promise.all` rejects as soon as any Promise rejects. If you need all results regardless of individual failures, use `Promise.allSettled`:

```js
const results = await Promise.allSettled([
  fetchUser(1),
  fetchUser(2),
  fetchUser(3),
]);

results.forEach(result => {
  if (result.status === "fulfilled") {
    console.log(result.value);
  } else {
    console.error(result.reason);
  }
});
```

Understanding what `async/await` compiles to makes all of this predictable. The syntax hides Promises, but the Promises are still there.
