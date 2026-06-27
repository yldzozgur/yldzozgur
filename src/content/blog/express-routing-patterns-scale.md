---
title: "Express routing patterns that don't turn into spaghetti at scale."
description: "A flat routes file works for 5 endpoints. Here are the patterns that keep an Express app navigable at 50 or 500 endpoints."
pubDate: 2024-04-29
tags: ["Node.js", "Express"]
draft: false
---

Most Express tutorials show all routes defined in `app.js`. That works for examples but falls apart when the application grows. Here are the patterns that keep routing maintainable.

## The router module pattern

Express's `Router` is a mini-app — it handles its own middleware and routes and can be mounted on a path.

```js
// routes/users.js
const { Router } = require("express");
const router = Router();

const { authenticate } = require("../middleware/auth");
const userController = require("../controllers/user");

router.get("/", authenticate, userController.list);
router.post("/", authenticate, userController.create);
router.get("/:id", authenticate, userController.getById);
router.put("/:id", authenticate, userController.update);
router.delete("/:id", authenticate, userController.delete);

module.exports = router;
```

```js
// app.js
const app = express();
const usersRouter = require("./routes/users");
const postsRouter = require("./routes/posts");

app.use("/users", usersRouter);
app.use("/posts", postsRouter);
```

The `/users` prefix is defined once in `app.js`. The router handles `GET /`, `POST /`, `GET /:id`, etc., which resolve to `GET /users`, `POST /users`, `GET /users/:id` when mounted.

## Nested routers

For nested resources:

```js
// routes/posts.js
const router = Router({ mergeParams: true }); // mergeParams lets nested routes see parent params

router.get("/", postController.list);
router.post("/", postController.create);

module.exports = router;

// routes/users.js
const postsRouter = require("./posts");

router.use("/:userId/posts", postsRouter);
// Now GET /users/:userId/posts works
```

`mergeParams: true` is required for the nested router to access `req.params.userId`. Without it, `req.params` only contains the nested router's own params.

## Controller pattern

Routes should not contain business logic. Extract handlers to controllers:

```js
// controllers/user.js
const userService = require("../services/user");

exports.list = async (req, res, next) => {
  try {
    const users = await userService.getAll(req.query);
    res.json(users);
  } catch (err) {
    next(err);
  }
};

exports.create = async (req, res, next) => {
  try {
    const user = await userService.create(req.body);
    res.status(201).json(user);
  } catch (err) {
    next(err);
  }
};
```

The controller handles the HTTP layer: parsing request data, calling services, formatting responses. The service handles business logic.

## Route grouping by concern

Organize routes by domain concept, not by HTTP method:

```js
// routes/index.js — barrel file that mounts all routers
const { Router } = require("express");
const router = Router();

router.use("/auth", require("./auth"));
router.use("/users", require("./users"));
router.use("/posts", require("./posts"));
router.use("/comments", require("./comments"));
router.use("/media", require("./media"));

module.exports = router;

// app.js
app.use("/api/v1", require("./routes"));
```

The version prefix (`/api/v1`) is set once. Changing it or adding `v2` is one line.

## Middleware scoped to router

Middleware added to a router only applies to that router's routes:

```js
// routes/admin.js
const router = Router();
const { requireAdmin } = require("../middleware/auth");

// Apply to all routes in this router
router.use(requireAdmin);

router.get("/users", adminController.listAllUsers);
router.delete("/users/:id", adminController.deleteUser);

module.exports = router;
```

`requireAdmin` only runs for `/admin/*` routes. You do not have to add it to every route individually.

## Param middleware

For routes with a common `:id` pattern, `router.param` runs once per unique parameter value per request:

```js
// routes/users.js
router.param("userId", async (req, res, next, id) => {
  try {
    req.targetUser = await userService.getById(id);
    if (!req.targetUser) return res.status(404).json({ error: "User not found" });
    next();
  } catch (err) {
    next(err);
  }
});

// The user is already loaded when these run
router.get("/:userId", (req, res) => res.json(req.targetUser));
router.put("/:userId", userController.update);
router.delete("/:userId", userController.delete);
```

`router.param` eliminates the repeated "fetch the user, check if it exists" code in every handler.

## Route file structure

```
src/
  routes/
    index.js        # mounts all routers
    auth.js
    users.js
    posts.js
    comments.js
  controllers/
    user.js
    post.js
  services/
    user.js
    post.js
  middleware/
    auth.js
    validate.js
    error.js
  app.js
```

This structure is navigable because the location of any code is predictable. Authentication logic is in `middleware/auth.js`. User business logic is in `services/user.js`. User HTTP handlers are in `controllers/user.js`. User routes are in `routes/users.js`.

The pattern that causes spaghetti is putting too much in one place. The pattern that scales is separating concerns early.
