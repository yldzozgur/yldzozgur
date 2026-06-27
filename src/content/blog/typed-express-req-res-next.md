---
title: "Typed Express: req, res, next with types that don't lie."
description: "Express's default TypeScript types are loose. Here's how to get accurate types on req.body, req.params, res.json, and custom middleware."
pubDate: 2024-03-07
tags: ["TypeScript", "Node.js"]
draft: false
---

Express ships with TypeScript definitions, but the defaults are deliberately loose. `req.body` is typed as `any`. `req.params` is `Record<string, string>`. This is necessary for a general framework, but it means TypeScript cannot help you inside route handlers without some extra work.

## The default problem

```ts
app.post("/users", (req, res) => {
  const { name, email } = req.body; // name and email are both 'any'
  // TypeScript cannot catch typos or wrong field names
});
```

This compiles but provides no safety. Here's how to fix it.

## Typing req.body

Express's `Request` type accepts generics for body, params, query, and response:

```ts
import { Request, Response } from "express";

interface CreateUserBody {
  name: string;
  email: string;
  password: string;
}

app.post(
  "/users",
  (req: Request<{}, {}, CreateUserBody>, res: Response) => {
    const { name, email, password } = req.body;
    // name, email, password are all typed correctly
  }
);
```

The `Request` generic is `Request<Params, ResBody, ReqBody, Query>`. To type only the body, pass empty objects for the others.

## Typing req.params

```ts
interface UserParams {
  id: string; // URL params are always strings
}

app.get(
  "/users/:id",
  (req: Request<UserParams>, res: Response) => {
    const { id } = req.params; // id is string, not any
  }
);
```

Note that URL parameters are always strings even if you use them as numbers. Parse them explicitly:

```ts
const userId = parseInt(req.params.id, 10);
if (isNaN(userId)) {
  return res.status(400).json({ error: "Invalid user ID" });
}
```

## Typing req.query

```ts
interface UserListQuery {
  page?: string;
  limit?: string;
  search?: string;
}

app.get(
  "/users",
  (req: Request<{}, {}, {}, UserListQuery>, res: Response) => {
    const page = parseInt(req.query.page ?? "1", 10);
    const limit = parseInt(req.query.limit ?? "20", 10);
  }
);
```

Query parameters are also always strings (or arrays of strings). Type them as `string` or `string | undefined`, not as `number`.

## Typing res.json

The second generic on `Request` is the response body type, which flows to `res.json`:

```ts
interface UserResponse {
  id: number;
  name: string;
  email: string;
}

app.get(
  "/users/:id",
  async (req: Request<{ id: string }>, res: Response<UserResponse>) => {
    const user = await getUser(req.params.id);
    res.json(user); // TypeScript checks that user matches UserResponse
  }
);
```

## Custom middleware: extending Request

The most common use case is authentication middleware that adds the current user to `req`. Extend the `Request` type with module augmentation:

```ts
// types/express.d.ts
import { User } from "./models/User";

declare global {
  namespace Express {
    interface Request {
      user?: User;
    }
  }
}
```

Now every `req.user` in your codebase is typed as `User | undefined`.

In your auth middleware:

```ts
import { Request, Response, NextFunction } from "express";

async function authenticate(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.split(" ")[1];
  if (!token) {
    return res.status(401).json({ error: "No token" });
  }
  try {
    req.user = await verifyToken(token); // req.user is now typed
    next();
  } catch {
    res.status(401).json({ error: "Invalid token" });
  }
}
```

In protected routes:

```ts
app.get("/profile", authenticate, (req, res) => {
  if (!req.user) return res.status(401).json({ error: "Unauthorized" });
  res.json({ name: req.user.name }); // TypeScript knows req.user is User here
});
```

## Typed route handlers as functions

When handlers get complex, extract them as typed functions:

```ts
import { RequestHandler } from "express";

interface CreateUserParams {}
interface CreateUserResponse { id: number; name: string; }
interface CreateUserBody { name: string; email: string; password: string; }

const createUser: RequestHandler<
  CreateUserParams,
  CreateUserResponse,
  CreateUserBody
> = async (req, res) => {
  // req.body is fully typed
  // res.json expects CreateUserResponse
  const user = await userService.create(req.body);
  res.status(201).json({ id: user.id, name: user.name });
};

app.post("/users", createUser);
```

`RequestHandler` is the type for Express middleware and route handlers.

## A complete typed route

```ts
import { Router, Request, Response } from "express";
import { z } from "zod";

const router = Router();

const CreatePostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
});

type CreatePostBody = z.infer<typeof CreatePostSchema>;

router.post(
  "/",
  authenticate,
  async (req: Request<{}, {}, CreatePostBody>, res: Response) => {
    const parsed = CreatePostSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ errors: parsed.error.flatten() });
    }
    const post = await postService.create({
      ...parsed.data,
      authorId: req.user!.id,
    });
    res.status(201).json(post);
  }
);
```

The combination of Zod validation and typed generics gives you full type safety from the HTTP boundary to the service layer.
