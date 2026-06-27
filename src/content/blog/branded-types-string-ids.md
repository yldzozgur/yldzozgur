---
title: "Branded types: making string IDs impossible to mix up."
description: "Branded types add nominal typing to TypeScript's structural system, preventing assignment between semantically different types with the same structure."
pubDate: 2024-02-19
tags: ["TypeScript"]
draft: false
---

TypeScript uses structural typing. Two types are compatible if they have the same shape. This is usually convenient, but sometimes it lets you assign a `UserId` where a `PostId` is expected because both are `string`.

Branded types solve this by adding a nominal layer on top of the structural system.

## The problem

```ts
function getPost(userId: string, postId: string): Post {
  return db.posts.findOne({ userId, postId });
}

const uid = "user_abc123";
const pid = "post_xyz789";

getPost(pid, uid); // Compiles fine — arguments swapped!
```

TypeScript cannot help here because both parameters have the same type: `string`. Swapping them is a valid call that produces a bug at runtime.

## Branded types

A branded type is a type with an added "phantom" field that exists only in the type system, not at runtime:

```ts
type Brand<T, B> = T & { readonly __brand: B };

type UserId = Brand<string, "UserId">;
type PostId = Brand<string, "PostId">;
```

`UserId` and `PostId` are both `string` at runtime. But TypeScript treats them as different types because their `__brand` field has different literal values.

Now the function signature is:

```ts
function getPost(userId: UserId, postId: PostId): Post {
  return db.posts.findOne({ userId, postId });
}

getPost(pid, uid); // Error: Argument of type 'PostId' is not assignable to parameter of type 'UserId'
```

The compiler catches the swap.

## Creating branded values

You need a way to create branded values. The standard approach is a casting function:

```ts
function asUserId(id: string): UserId {
  return id as UserId;
}

function asPostId(id: string): PostId {
  return id as PostId;
}

const uid = asUserId("user_abc123");
const pid = asPostId("post_xyz789");

getPost(uid, pid); // OK
getPost(pid, uid); // Error
```

The cast is the only place where the unsafe operation happens. Everywhere else in the codebase, the types enforce correct usage.

## Validated branded types

A more powerful pattern: validate during branding.

```ts
type Email = Brand<string, "Email">;

function parseEmail(raw: string): Email {
  if (!raw.includes("@")) {
    throw new Error(`Invalid email: ${raw}`);
  }
  return raw as Email;
}

function sendEmail(to: Email, subject: string): void {
  // We know `to` was validated when it was branded
}
```

Once a string is branded as `Email`, any function that accepts `Email` can trust that it was validated. The validation happens once at the entry point.

## Numeric IDs

Branded types work for numeric IDs too:

```ts
type UserId = Brand<number, "UserId">;
type OrderId = Brand<number, "OrderId">;

function cancelOrder(orderId: OrderId, userId: UserId): void {
  db.orders.update(orderId, { status: "cancelled", cancelledBy: userId });
}
```

Without branding, `cancelOrder(userId, orderId)` compiles because both are `number`. With branding, the swap is caught.

## Opaque types with utility

You can add methods to branded types using intersection:

```ts
type Dollars = Brand<number, "Dollars"> & {
  add(other: Dollars): Dollars;
  format(): string;
};
```

But in practice, keeping branded types as simple overlaid tags is usually cleaner. The value is the type safety, not the methods.

## A full example

```ts
type Brand<T, B> = T & { readonly __brand: B };

type UserId = Brand<string, "UserId">;
type SessionToken = Brand<string, "SessionToken">;
type HashedPassword = Brand<string, "HashedPassword">;

function createUser(
  email: string,
  password: string
): { id: UserId; token: SessionToken } {
  const hashed = hashPassword(password) as HashedPassword;
  const id = generateId() as UserId;
  const token = generateToken() as SessionToken;
  db.users.create({ id, email, password: hashed });
  return { id, token };
}

function deleteUser(id: UserId, token: SessionToken): void {
  if (!verifyToken(token, id)) throw new Error("Unauthorized");
  db.users.delete(id);
}

const { id, token } = createUser("alice@example.com", "secret");
deleteUser(id, token); // correct
deleteUser(token, id); // Error: SessionToken is not assignable to UserId
```

## Where to draw the line

Branded types add ceremony. Every ID needs a casting function, every boundary where the ID enters the system (HTTP request, database result) needs an explicit cast. This is deliberate — the casts are the places where you accept external data and vouch for it.

Use branded types for:
- IDs that are semantically different types but structurally identical
- Values that must be validated before use (emails, phone numbers, URLs)
- Sensitive values you want to track explicitly (tokens, hashed passwords)

Skip them for:
- Types that are structurally different (no risk of confusion)
- Internal utilities where the overhead outweighs the benefit

The goal is to put the unsafe cast in one place and let the type system enforce correct usage everywhere else.
