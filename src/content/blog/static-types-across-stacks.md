---
title: "Static typing in Java vs TypeScript — a beginner's side-by-side"
description: "Both languages catch bugs before you run the code, but they do it differently. A simple walkthrough using a small payment example."
pubDate: 2026-05-14
tags: ["typescript", "code-review", "tooling"]
draft: false
---

If you read Java code first and then TypeScript code, the two can look very similar. `List<User>` in Java becomes `User[]` in TypeScript. `Map<K, V>` looks the same. But the moment you try to model something with **more than one shape** — like a payment that can be a card charge, a bank transfer, or a refund — the two type systems start to behave very differently.

This post takes one tiny example and writes it in both languages. The goal is not to pick a winner. The goal is to see *what each language asks you to write down*, and what it does in return.

## The example

Let's say we want to handle a payment. A payment can be one of three things:

| Variant | Common fields | Unique field |
|---|---|---|
| Card charge | `id`, `amount` | `last4` (last 4 digits) |
| Bank transfer | `id`, `amount` | `iban` |
| Refund | `id`, `amount` | `originalId` (the payment being refunded) |

That's it. Three shapes that share two fields and add one.

## In Java

Modern Java (17+) lets us write this with **sealed interfaces** and **records**:

```java
public sealed interface Payment
    permits CardPayment, BankTransfer, Refund {}

public record CardPayment(String id, BigDecimal amount, String last4)     implements Payment {}
public record BankTransfer(String id, BigDecimal amount, String iban)     implements Payment {}
public record Refund(String id, BigDecimal amount, String originalId)     implements Payment {}
```

Two things to notice:

1. **`sealed interface`** means: "the *complete* list of payments is right here." Nobody else can add a fourth variant from another file.
2. **`record`** is a short way to say "this is a small immutable data class." Java generates the constructor, getters, and `equals` for free.

Now we can describe any payment:

```java
String describe(Payment p) {
    return switch (p) {
        case CardPayment c    -> "Card ending " + c.last4();
        case BankTransfer b   -> "Transfer to " + b.iban();
        case Refund r         -> "Refund of " + r.originalId();
    };
}
```

The cool part: if you **forget a case**, the compiler refuses to build. And if someone adds a fourth variant later, every `switch` like this becomes an error pointing exactly where you need to add a branch.

That's a strong promise. The cost is verbosity — three separate `record` declarations to describe one concept.

## In TypeScript

The same example with a **discriminated union**:

```ts
type Payment =
  | { kind: "card";   id: string; amount: number; last4: string }
  | { kind: "bank";   id: string; amount: number; iban: string }
  | { kind: "refund"; id: string; amount: number; originalId: string };
```

The trick is the `kind` field. It's a string that tells the compiler *which variant we're looking at*. Now we can describe a payment the same way:

```ts
function describe(p: Payment): string {
  switch (p.kind) {
    case "card":   return `Card ending ${p.last4}`;
    case "bank":   return `Transfer to ${p.iban}`;
    case "refund": return `Refund of ${p.originalId}`;
  }
}
```

Inside `case "card"`, TypeScript knows for sure that `p.last4` exists. Inside `case "bank"`, it knows `p.iban` exists. You don't have to cast or check — the compiler narrows the type for you based on `kind`.

But what about the "you forgot a case" guarantee? TypeScript doesn't give it automatically. You get it by writing a tiny helper:

```ts
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function describe(p: Payment): string {
  switch (p.kind) {
    case "card":   return `Card ending ${p.last4}`;
    case "bank":   return `Transfer to ${p.iban}`;
    case "refund": return `Refund of ${p.originalId}`;
    default:       return assertNever(p);
  }
}
```

The trick: in the `default` branch, `p` should be **`never`** (no variants left). If you add a fourth variant to the union and forget to handle it, `p` isn't `never` anymore — and `assertNever(p)` becomes a compile error.

So you get the same safety, just opt-in.

## What carries over

If you know one type system, here is what reads almost the same in the other:

| Concept | Java | TypeScript |
|---|---|---|
| Set of fixed variants | `sealed interface` | discriminated union |
| Small data class | `record` | `type` or `interface` |
| "Maybe missing" | `Optional<T>` | `T \| undefined` |
| Generic with a bound | `<T extends Foo>` | `<T extends Foo>` |
| Anything iterable | `Iterable<T>` | `Iterable<T>` |

The intuitions are the same. If you can read `Map<String, List<Order>>` in Java, you can read `Map<string, Order[]>` in TypeScript without help.

## What does *not* carry over

Three things look similar but behave differently. These are where most bugs cross the language boundary.

### 1. Exceptions

Java has **checked exceptions** — the compiler forces you to declare or handle them. TypeScript has none. Idiomatic TypeScript usually models errors as values:

```ts
type Result<T, E> =
  | { ok: true;  value: T }
  | { ok: false; error: E };

async function getUser(id: string): Promise<Result<User, "not-found" | "db-error">> {
  // ...
}
```

It's the same discriminated-union trick again. That's why you see it everywhere in TypeScript codebases — it's the language's answer to "how do I represent failure."

### 2. Numbers

Java has many: `int`, `long`, `double`, `BigDecimal`. TypeScript has just one: `number` (and `bigint` for huge integers). Storing **money** as `number` in TypeScript will quietly lose cents to floating-point math.

The TypeScript answer is to use a decimal library (like `decimal.js`) or store amounts as **integer cents** and format them at the display layer.

### 3. Same shape, different meaning

This is the deepest difference.

Java is **nominal**: two classes with identical fields are still different types.

```java
class UserId { String value; }
class OrderId { String value; }

UserId u = new UserId(...);
OrderId o = u; // ❌ won't compile
```

TypeScript is **structural**: any object with the right shape is assignable.

```ts
type UserId = string;
type OrderId = string;

const u: UserId = "abc";
const o: OrderId = u; // ✅ compiles fine 😬
```

That's useful sometimes (no boilerplate) and dangerous others (a `userId` ends up where an `orderId` should be). The fix is a **branded type**:

```ts
type UserId  = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };
```

Now `UserId` and `OrderId` are different types at compile time, even though they're both strings at runtime. You get some of Java's nominal safety back, but you have to ask for it.

## The runtime question

There is one last thing that matters in practice. Java keeps some type information at runtime (you can `instanceof` a `Payment`). TypeScript erases all type information when it compiles to JavaScript. After `tsc` runs, **the types are gone**.

So how do you validate a JSON request body in a TypeScript backend? You can't ask "is this a `Payment`?" at runtime — the answer is meaningless. You use a **schema library** like [zod](https://zod.dev) or [valibot](https://valibot.dev):

```ts
import { z } from "zod";

const PaymentSchema = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("card"),   id: z.string(), amount: z.number(), last4: z.string() }),
  z.object({ kind: z.literal("bank"),   id: z.string(), amount: z.number(), iban: z.string() }),
  z.object({ kind: z.literal("refund"), id: z.string(), amount: z.number(), originalId: z.string() }),
]);

type Payment = z.infer<typeof PaymentSchema>;
```

Now `Payment` is the type *and* `PaymentSchema.parse(req.body)` is the runtime check. Same source, two outputs.

This split — types at compile time, schemas at runtime — is the part most people don't realize when they move from a JVM stack to Node. The compiler isn't doing less. It's doing **exactly as much**, on exactly the part of the program where you control the source of truth. The boundary (input from network, database, user) is where you, the developer, layer in validation.

## Takeaway

Both languages catch bugs before they run. They just charge for the catch differently.

- **Java** asks for more code upfront (`sealed interface`, `record`, exception declarations) and gives you compile-time *and* runtime guarantees in return.
- **TypeScript** asks for less code upfront (one union, one helper) and gives you compile-time guarantees only — runtime validation is your job, but it's deliberate and explicit.

The smaller lesson is portable: when you cross stacks, **look for the pattern, not the syntax**. A sealed interface and a discriminated union are the same idea wearing different uniforms. Once you see that, every new language stops being a fresh start.
