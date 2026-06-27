---
title: "RBAC: the middleware pattern that scales from 2 roles to 20."
description: "Role-based access control implemented as Express middleware — a clean pattern that keeps authorization logic out of route handlers and scales without becoming unmanageable."
pubDate: 2024-07-15
tags: ["Security"]
draft: false
---

Authorization is the part of authentication that most tutorials skip. They show you how to verify a token but not how to decide what the verified user is allowed to do. Role-based access control (RBAC) is the most common pattern, and a middleware-based implementation keeps it maintainable as your role set grows.

## The core model

RBAC assigns users to roles, and roles to permissions. A user can have multiple roles. The system checks whether any of their roles grants the required permission.

```
User → [roles] → each role → [permissions]
```

Simple example:
- `admin` role: `read:users`, `write:users`, `delete:users`, `read:reports`
- `editor` role: `read:users`, `write:posts`
- `viewer` role: `read:posts`

A user with the `editor` role cannot delete users. A user with both `editor` and `viewer` has the union of both sets.

## Storing roles in the JWT

The simplest approach embeds roles in the access token:

```js
// On login
const token = jwt.sign(
  {
    sub: user._id.toString(),
    roles: user.roles, // ["editor", "viewer"]
  },
  process.env.JWT_SECRET,
  { expiresIn: "15m" }
);
```

This is stateless — no database lookup needed on each request. The tradeoff: if you change a user's roles, they keep the old roles until their token expires. For most applications a 15-minute window is acceptable.

## Defining permissions

Keep permissions in a central config, not scattered across route files:

```js
// permissions.js
export const ROLE_PERMISSIONS = {
  admin: [
    "read:users",
    "write:users",
    "delete:users",
    "read:reports",
    "write:reports",
  ],
  editor: [
    "read:users",
    "write:posts",
    "read:posts",
    "publish:posts",
  ],
  viewer: [
    "read:posts",
  ],
  moderator: [
    "read:posts",
    "delete:posts",
    "read:users",
  ],
};

export function hasPermission(roles, requiredPermission) {
  return roles.some((role) =>
    ROLE_PERMISSIONS[role]?.includes(requiredPermission)
  );
}
```

This is the file you update when requirements change. Route files never need to change when you add a new role.

## The middleware

Two middleware functions: one to attach the user, one to check permissions.

```js
// middleware/auth.js
import jwt from "jsonwebtoken";

export function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "No token provided" });
  }

  try {
    const token = authHeader.slice(7);
    req.user = jwt.verify(token, process.env.JWT_SECRET, {
      algorithms: ["HS256"],
    });
    next();
  } catch (err) {
    return res.status(401).json({ error: "Invalid token" });
  }
}

export function authorize(...requiredPermissions) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: "Not authenticated" });
    }

    const userRoles = req.user.roles ?? [];
    const hasAll = requiredPermissions.every((perm) =>
      hasPermission(userRoles, perm)
    );

    if (!hasAll) {
      return res.status(403).json({ error: "Insufficient permissions" });
    }

    next();
  };
}
```

## Using it on routes

```js
import { authenticate, authorize } from "./middleware/auth.js";

// Public route
app.get("/posts", getPosts);

// Must be logged in
app.get("/dashboard", authenticate, getDashboard);

// Must have specific permission
app.post("/posts", authenticate, authorize("write:posts"), createPost);

// Must have multiple permissions
app.delete("/posts/:id", authenticate, authorize("delete:posts"), deletePost);

// Admin only
app.get("/admin/users",
  authenticate,
  authorize("read:users"),
  listUsers
);

app.delete("/admin/users/:id",
  authenticate,
  authorize("delete:users"),
  deleteUser
);
```

The route handler itself contains zero authorization logic. It only runs if the middleware allows it through.

## Checking permissions inside handlers

Sometimes you need conditional behavior based on role — for example, showing extra fields to admins:

```js
function getUser(req, res) {
  const user = await db.users.findById(req.params.id);

  // Base response for everyone
  const response = {
    id: user._id,
    name: user.name,
    createdAt: user.createdAt,
  };

  // Extra fields only for admins
  if (hasPermission(req.user.roles, "read:users:sensitive")) {
    response.email = user.email;
    response.loginCount = user.loginCount;
  }

  res.json(response);
}
```

## Scaling beyond simple roles

When you reach ~10+ roles or need per-resource permissions ("can edit this specific post"), flat RBAC starts to strain. Two common extensions:

**Hierarchical roles**: roles inherit from other roles. `admin` inherits all `editor` permissions plus more. Implement by flattening the hierarchy when building the permissions set.

**Attribute-based checks (ABAC)**: permissions depend on the resource's attributes, not just the user's role. "User can edit posts they authored." This moves beyond pure RBAC:

```js
async function updatePost(req, res) {
  const post = await db.posts.findById(req.params.id);

  const isAuthor = post.authorId.equals(req.user.sub);
  const canEditAny = hasPermission(req.user.roles, "write:posts:any");

  if (!isAuthor && !canEditAny) {
    return res.status(403).json({ error: "Cannot edit this post" });
  }

  // proceed
}
```

Start with flat RBAC. Add hierarchy or attribute checks only when flat roles genuinely can't express your requirements. The middleware pattern described here accommodates these extensions without restructuring your routes.
