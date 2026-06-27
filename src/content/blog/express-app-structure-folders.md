---
title: "Express app structure: the folders that keep a growing codebase navigable."
description: "A flat Express project works until it doesn't. Here's a folder structure that separates concerns, scales with the project, and stays readable for new contributors."
pubDate: 2024-05-27
tags: ["Express", "Node.js"]
draft: false
---

Express is unopinionated about folder structure. That's a feature, but it means every project starts fresh. Most tutorials put everything in `index.js`, which works for demos but creates problems as the app grows. Here's a structure that handles a real application.

## The structure

```
project/
├── src/
│   ├── app.js           # Express app setup (no server.listen)
│   ├── server.js        # Binds to a port, starts the app
│   ├── routes/          # Route definitions
│   │   ├── index.js     # Mounts all routers
│   │   ├── users.js
│   │   └── posts.js
│   ├── controllers/     # Route handlers
│   │   ├── users.js
│   │   └── posts.js
│   ├── middleware/      # Custom middleware
│   │   ├── auth.js
│   │   ├── validate.js
│   │   └── errorHandler.js
│   ├── services/        # Business logic
│   │   ├── userService.js
│   │   └── postService.js
│   ├── models/          # Database models or query functions
│   │   ├── user.js
│   │   └── post.js
│   └── config/          # Configuration
│       ├── index.js
│       └── database.js
├── tests/
├── .env
└── package.json
```

## Why separate `app.js` from `server.js`

`app.js` sets up Express without starting the server:

```js
// src/app.js
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const routes = require('./routes');
const errorHandler = require('./middleware/errorHandler');

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());
app.use('/api/v1', routes);
app.use(errorHandler);

module.exports = app;
```

`server.js` imports the app and binds it to a port:

```js
// src/server.js
const app = require('./app');

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

This separation lets your tests import `app` directly without starting a real server, which is what libraries like Supertest expect.

## Routes vs controllers

Routes define the URL and method; controllers contain the handler logic.

```js
// src/routes/users.js
const express = require('express');
const router = express.Router();
const usersController = require('../controllers/users');
const { requireAuth } = require('../middleware/auth');
const { validateBody } = require('../middleware/validate');
const { createUserSchema } = require('./schemas/users');

router.get('/', usersController.list);
router.post('/', validateBody(createUserSchema), usersController.create);
router.get('/:id', usersController.getById);
router.put('/:id', requireAuth, usersController.update);
router.delete('/:id', requireAuth, usersController.remove);

module.exports = router;
```

```js
// src/controllers/users.js
const userService = require('../services/userService');

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

Controllers are thin. They translate HTTP into service calls and service results into HTTP responses. No business logic lives here.

## Services

Business logic goes in services:

```js
// src/services/userService.js
const User = require('../models/user');
const { AppError } = require('../utils/errors');

exports.create = async ({ email, password, name }) => {
  const existing = await User.findByEmail(email);
  if (existing) throw new AppError('Email already in use', 409);

  const hashedPassword = await bcrypt.hash(password, 12);
  return User.create({ email, password: hashedPassword, name });
};

exports.getAll = async ({ page = 1, limit = 20 }) => {
  return User.findAll({ page: Number(page), limit: Number(limit) });
};
```

Services don't know about `req` or `res`. They take plain data and return plain data. This makes them testable without an HTTP layer.

## The routes index

A single file mounts all routers:

```js
// src/routes/index.js
const express = require('express');
const router = express.Router();

router.use('/users', require('./users'));
router.use('/posts', require('./posts'));

module.exports = router;
```

Adding a new resource means adding one line here and creating two files: `routes/newResource.js` and `controllers/newResource.js`.

## Config

Environment-specific configuration in one place:

```js
// src/config/index.js
module.exports = {
  port: process.env.PORT || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',
  db: {
    url: process.env.DATABASE_URL,
    poolSize: parseInt(process.env.DB_POOL_SIZE || '10'),
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },
};
```

Import from `../config` anywhere in the app instead of reading `process.env` directly. This makes it easy to add validation or defaults without changing every file that uses a config value.

## What to ignore

Not every app needs this full structure. A project with three routes and no team doesn't need a `services/` layer. Add folders when you actually have multiple files that belong in them. The structure above is a ceiling, not a requirement.
