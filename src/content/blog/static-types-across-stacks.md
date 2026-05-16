---
title: "Static typing in Java vs TypeScript, a beginner's side by side"
description: "Both languages catch bugs before you run the code, but they handle it differently. A simple walkthrough using a small payment example."
pubDate: 2026-05-14
tags: ["typescript", "code-review", "tooling"]
draft: false
---

If you read some Java first and then read some TypeScript, the two can feel pretty similar. `List<User>` becomes `User[]`. `Map<K, V>` is `Map<K, V>` in both. So far so good.

But the moment you try to model something with more than one shape, like a payment that could be a card charge, a bank transfer, or a refund, the two type systems stop looking alike. That's where they start showing what they actually believe about correctness.

I want to take one small example and write it in both languages. Not to pick a winner. Both languages ship to production every day. I just want to see what each one asks you to write down, and what it gives you back.

## The example

A payment can be one of three things:

| Variant | Common fields | Unique field |
|---|---|---|
| Card charge | `id`, `amount` | `last4` (last 4 digits) |
| Bank transfer | `id`, `amount` | `iban` |
| Refund | `id`, `amount` | `originalId` (the payment being refunded) |

Three shapes. Two shared fields. One unique field each. Nothing fancy.

## In Java

Modern Java (17 and up) gives you sealed interfaces and records:

```java
public sealed interface Payment
    permits CardPayment, BankTransfer, Refund {}

public record CardPayment(String id, BigDecimal amount, String last4)     implements Payment {}
public record BankTransfer(String id, BigDecimal amount, String iban)     implements Payment {}
public record Refund(String id, BigDecimal amount, String originalId)     implements Payment {}
```

Two things going on here.

The word `sealed` is the important one. It tells the compiler "the full list of payments is right here. Nobody else can sneak in a fourth variant from another file."

The other word is `record`. Think of it as a shortcut for a small immutable data class. Java fills in the constructor, the getters, and `equals` for you.

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

The nice thing: forget a case and the compiler refuses to build. Add a fourth variant later and every `switch` like this becomes an error that points exactly where you need a new branch. That's a strong promise.

The cost is verbosity. Three separate record declarations for one idea.

## In TypeScript

Same example, written as a discriminated union:

```ts
type Payment =
  | { kind: "card";   id: string; amount: number; last4: string }
  | { kind: "bank";   id: string; amount: number; iban: string }
  | { kind: "refund"; id: string; amount: number; originalId: string };
```

The trick is that `kind` field. It's just a string, but the compiler uses it to figure out which variant you're looking at right now.

```ts
function describe(p: Payment): string {
  switch (p.kind) {
    case "card":   return `Card ending ${p.last4}`;
    case "bank":   return `Transfer to ${p.iban}`;
    case "refund": return `Refund of ${p.originalId}`;
  }
}
```

Inside `case "card"`, TypeScript knows `p.last4` is there. Inside `case "bank"`, it knows `p.iban` is there. You don't cast, you don't double-check. The compiler narrows the type based on the `kind` value.

What about the "you forgot a case" guarantee? TypeScript doesn't give it for free. You opt in with a tiny helper:

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

In the `default` branch, `p` should be `never`. No variants left. If you add a fourth one to the union and forget to handle it, suddenly `p` isn't `never` anymore, and `assertNever(p)` becomes a compile error.

Same safety as Java's exhaustive switch. You just have to ask for it.

## What carries across

Some patterns map almost one to one between the two:

| Concept | Java | TypeScript |
|---|---|---|
| Closed set of variants | `sealed interface` | discriminated union |
| Small data class | `record` | `type` or `interface` |
| Maybe missing | `Optional<T>` | `T \| undefined` |
| Generic with a bound | `<T extends Foo>` | `<T extends Foo>` |
| Anything iterable | `Iterable<T>` | `Iterable<T>` |

If you can read `Map<String, List<Order>>` in Java, `Map<string, Order[]>` reads itself.

## What doesn't carry across

A few things look familiar but behave differently. These are usually where bugs slip when someone moves between the two.

### Exceptions

Java has checked exceptions. The compiler makes you declare or catch them. TypeScript has none.

So idiomatic TypeScript codebases lean on error values:

```ts
type Result<T, E> =
  | { ok: true;  value: T }
  | { ok: false; error: E };

async function getUser(id: string): Promise<Result<User, "not-found" | "db-error">> {
  // ...
}
```

That's the same discriminated union trick again. You see it everywhere in TypeScript because it's the language's answer to "how do I represent failure without throwing."

### Numbers

Java distinguishes between `int`, `long`, `double`, and `BigDecimal`. TypeScript has one number type. It's an IEEE-754 double, which is fine for most things and quietly wrong for money.

If you store cents as `number` in TypeScript, you'll eventually have a bug like `0.1 + 0.2 = 0.30000000000000004`. The usual fix is either a decimal library, or store the amount as an integer (in cents) and format it for display.

### Same shape, different meaning

This one is deeper. Java is nominal. Two classes with the same fields are still different types.

```java
class UserId { String value; }
class OrderId { String value; }

UserId u = new UserId(...);
OrderId o = u; // won't compile
```

TypeScript is structural. Any object with the right shape is assignable, full stop.

```ts
type UserId = string;
type OrderId = string;

const u: UserId = "abc";
const o: OrderId = u; // compiles, ouch
```

Sometimes that's a feature (less boilerplate). Sometimes it's a footgun (a user id ends up where an order id should be). The workaround is what people call a "branded type":

```ts
type UserId  = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };
```

Now `UserId` and `OrderId` are incompatible at compile time, even though they're both just strings at runtime. You get some of Java's nominal safety back, but you have to ask for it.

## The runtime question

Here's the last thing that matters in practice.

Java keeps some type info around at runtime. You can do `obj instanceof Payment` and get a real answer. TypeScript erases all the types when it compiles to JavaScript. After `tsc` runs, the types are completely gone.

So how do you check a JSON request body in a TypeScript backend? You can't ask "is this a `Payment`?" because at runtime, that question is meaningless. The usual answer is a schema library like [zod](https://zod.dev):

```ts
import { z } from "zod";

const PaymentSchema = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("card"),   id: z.string(), amount: z.number(), last4: z.string() }),
  z.object({ kind: z.literal("bank"),   id: z.string(), amount: z.number(), iban: z.string() }),
  z.object({ kind: z.literal("refund"), id: z.string(), amount: z.number(), originalId: z.string() }),
]);

type Payment = z.infer<typeof PaymentSchema>;
```

Now `Payment` is the static type, and `PaymentSchema.parse(req.body)` does the runtime check. Same source. Two outputs.

This split (types at compile time, schemas at runtime) is the part most people miss when they switch from a JVM backend to a Node one. The compiler isn't doing less work. It's doing the same amount, just on a different surface. The boundary, where untyped JSON enters your code, is on you.

## The takeaway

Both languages catch bugs before they run. They just charge for it differently.

Java asks for more code upfront (sealed interface, record, exception declarations) and gives you compile-time and runtime guarantees in return. TypeScript asks for less code upfront (one union, one helper) and gives you compile-time guarantees only. The runtime layer is your job, but it's explicit, and the schema doubles as the type.

The useful part is that this carries over. When you move between languages, it helps to look for the pattern instead of the syntax. A sealed interface and a discriminated union are the same idea written two ways, and once you notice that, the next language is easier to pick up.
