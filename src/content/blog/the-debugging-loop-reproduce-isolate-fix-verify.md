---
title: "The debugging loop: reproduce, isolate, fix, verify."
description: "A structured approach to debugging that works across languages, systems, and types of bugs."
pubDate: 2025-07-24
tags: ["DevOps"]
draft: false
---

Debugging without a method is archaeology. You dig through code hoping to find something familiar that looks wrong. Sometimes it works. More often it wastes time and leaves you less certain than when you started.

A structured debugging loop works consistently across languages, systems, and types of problems. The steps are: reproduce, isolate, fix, verify.

## Step 1: Reproduce

Before you read a single line of code, get the bug to happen in front of you. A bug you cannot reproduce is a bug you cannot verify you have fixed.

The goal is the minimum reproducible case. Start with the exact conditions reported. Then reduce them.

If a bug is reported as "the checkout fails when the user has more than 10 items in their cart from the sale category after applying a coupon", test each condition independently:

- Does it fail with 11 regular items?
- Does it fail with sale items regardless of coupon?
- Does the coupon matter?

Strip the problem down until you have the smallest possible input that triggers the failure. This compression almost always reveals what the bug is before you start reading code.

Write the repro case as a test:

```python
def test_checkout_fails_with_11_sale_items():
    cart = Cart()
    for i in range(11):
        cart.add_item(Item(category='sale', price=9.99))
    
    result = checkout(cart, coupon=None)
    assert result.success  # This should pass
```

Now you have an automated repro that will tell you when the bug is fixed and prevent it from coming back.

## Step 2: Isolate

With a reproducible case, the next step is finding where the fault actually is. The bug is somewhere. Your job is to narrow the search space.

**Binary search the call stack.** Pick the midpoint of the execution path and check whether state is correct there. If state is wrong at the midpoint, the bug is in the first half. If state is correct at the midpoint, the bug is in the second half. Repeat.

```python
def checkout(cart, coupon):
    validated_cart = validate_cart(cart)          # Check state here first
    discounted = apply_discount(validated_cart, coupon)
    result = process_payment(discounted)
    return result
```

Add a temporary assertion or log at the midpoint:

```python
def checkout(cart, coupon):
    validated_cart = validate_cart(cart)
    print(f"DEBUG: validated_cart item count = {len(validated_cart.items)}")
    # Is this correct? If not, bug is in validate_cart.
    # If correct, bug is in apply_discount or process_payment.
```

This is faster than reading every line of every function sequentially.

**Check assumptions explicitly.** Most bugs are violated assumptions. You believe a value is never None, always a positive integer, always within a certain range. State these assumptions as assertions and see which one fails:

```python
def apply_discount(cart, coupon):
    assert cart is not None, "cart should not be None here"
    assert len(cart.items) > 0, "cart should have items"
    assert all(item.price > 0 for item in cart.items), "all prices should be positive"
```

The assertion that fails tells you exactly which assumption was wrong.

**Read error messages carefully.** The error message usually tells you the file and line number. Go there first. Read the actual message. Many debugging sessions waste 20 minutes because the developer started reading code before reading the error.

## Step 3: Fix

Once you know what is wrong, the fix is often obvious. Sometimes it is not, and the challenge is fixing the root cause rather than the symptom.

A symptom fix silences the error without addressing why it happens. A root cause fix makes the condition impossible. Prefer root cause fixes.

Symptom fix:
```python
def apply_discount(cart, coupon):
    if not cart or not cart.items:  # Added to prevent crash
        return cart
```

Root cause fix: find out why `cart` is arriving in an invalid state and fix that.

Document the fix with a comment that explains the why:

```python
# validate_cart was stripping sale items when item count > 10 due to
# an off-by-one in the slice index. The bug was introduced in commit abc123.
# The correct slice is items[:10] (exclusive), not items[:11].
validated_items = cart.items[:10]
```

## Step 4: Verify

Run the repro test you wrote in step 1. It should pass.

Then run the full test suite. A fix that breaks three other tests is not done.

Check the fix in the same environment where the bug was reported. Bugs that are hard to reproduce locally can behave differently in production due to environment differences - different data, different timing, different configuration.

If the fix involves a race condition, timing issue, or intermittent behavior, run the test many times:

```bash
for i in $(seq 1 100); do pytest test_checkout.py::test_checkout_fails_with_11_sale_items; done
```

A test that fails 1 in 100 runs tells you the fix is incomplete.

## The common shortcuts that backfire

Adding `try/except` around the failing line without understanding why it fails produces silent failures. The error disappears from logs. The actual problem persists, now undetected.

Restarting the service without reproducing the bug first wastes the crash context. The next occurrence of the bug might not leave enough information to diagnose it.

Asking "what changed recently" before reproducing is sometimes useful but often leads to reverting unrelated changes that happened to precede the report.

The loop - reproduce, isolate, fix, verify - compresses debugging time by eliminating the phases where you are searching without a signal.
