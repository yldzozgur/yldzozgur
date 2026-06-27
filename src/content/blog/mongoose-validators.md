---
title: "Mongoose validators: catching bad data before it reaches the database."
description: "Mongoose schema validation runs before writes and can be customized beyond built-in types. Here's how built-in, custom, and async validators work and when to use each."
pubDate: 2024-08-08
tags: ["Security"]
draft: false
---

MongoDB accepts any document you send it. That flexibility is useful, but it means an application that doesn't validate input can store malformed data that causes errors later — in queries that assume a specific shape, in code that expects an email to be an email, or in reports that can't compute totals because a price field contains a string.

Mongoose validation runs before every `save()` and `insertMany()` call, and it's configurable at the schema level.

## Built-in validators

The schema type itself is the first validator:

```js
import mongoose from "mongoose";
const { Schema } = mongoose;

const userSchema = new Schema({
  email: {
    type: String,
    required: true,          // must be present
    unique: true,            // creates an index (not a validator)
    lowercase: true,         // transform, not validation
    trim: true,              // transform
    minlength: 3,
    maxlength: 254,
  },
  age: {
    type: Number,
    min: 0,
    max: 150,
  },
  role: {
    type: String,
    enum: ["user", "editor", "admin"],
    default: "user",
  },
  website: {
    type: String,
    match: /^https?:\/\/.+/,   // regex validator
  },
});
```

These run automatically:
- `required`: fails if the field is missing or undefined
- `minlength`/`maxlength`: for strings
- `min`/`max`: for numbers and dates
- `enum`: value must be one of the listed options
- `match`: value must match the regex

When validation fails, Mongoose throws a `ValidationError` before the database write happens:

```js
try {
  const user = new User({ email: "not-an-email", age: -5, role: "superuser" });
  await user.save();
} catch (err) {
  if (err.name === "ValidationError") {
    console.log(err.errors);
    // {
    //   age: { message: "Path `age` (-5) is less than minimum allowed value (0)." },
    //   role: { message: "`superuser` is not a valid enum value for path `role`." }
    // }
  }
}
```

## Custom validators

Built-in validators cover common cases. Custom validators handle anything else:

```js
const userSchema = new Schema({
  email: {
    type: String,
    required: true,
    validate: {
      validator: function(v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
      },
      message: props => `${props.value} is not a valid email address`,
    },
  },
  phone: {
    type: String,
    validate: {
      validator: function(v) {
        if (!v) return true; // optional field — only validate if present
        return /^\+?[\d\s\-().]{7,15}$/.test(v);
      },
      message: "Invalid phone number format",
    },
  },
  tags: {
    type: [String],
    validate: {
      validator: function(arr) {
        return arr.length <= 10;
      },
      message: "Cannot have more than 10 tags",
    },
  },
});
```

The `validator` function receives the field value and returns a boolean. Return `false` to fail validation.

## Async validators

When validation requires a database lookup — checking uniqueness beyond what the unique index handles, or verifying a referenced document exists — use an async validator:

```js
const postSchema = new Schema({
  slug: {
    type: String,
    required: true,
    validate: {
      validator: async function(v) {
        // Check uniqueness, but exclude the current document on updates
        const count = await Post.countDocuments({
          slug: v,
          _id: { $ne: this._id },
        });
        return count === 0;
      },
      message: "Slug must be unique",
    },
  },
  categoryId: {
    type: Schema.Types.ObjectId,
    ref: "Category",
    validate: {
      validator: async function(id) {
        const category = await Category.findById(id);
        return category !== null;
      },
      message: "Category does not exist",
    },
  },
});
```

Note: async validators don't run on bulk operations like `insertMany` or `updateMany`. They only run when you use `save()`, `create()`, or explicitly call `validate()`.

## Running validation explicitly

Sometimes you want to validate without saving:

```js
const user = new User({ email: "invalid" });
try {
  await user.validate();
} catch (err) {
  console.log(err.errors);
}
```

Or validate a specific path:

```js
await user.validate("email");
```

## Validation on updates

By default, Mongoose does not run validators on `findOneAndUpdate()`, `updateOne()`, or similar operations. Add `runValidators: true`:

```js
await User.findOneAndUpdate(
  { _id: userId },
  { age: -1 },
  { runValidators: true, new: true }
);
// throws ValidationError: age must be >= 0
```

Keep in mind that `this` is not available in validators when run on update operations — async validators that reference `this._id` for uniqueness checks won't work as expected on updates.

## Structuring validation in a team

A few conventions that help:

Keep validation in the schema, not in route handlers. Route handlers should not contain `if (!email.includes('@'))` checks. That logic belongs in the schema.

Use the error structure Mongoose returns. In your Express error handler, detect `ValidationError` and format the response:

```js
app.use((err, req, res, next) => {
  if (err.name === "ValidationError") {
    const errors = Object.values(err.errors).map((e) => ({
      field: e.path,
      message: e.message,
    }));
    return res.status(400).json({ errors });
  }
  next(err);
});
```

Validators are not a substitute for sanitization. Mongoose validators check data shape. Strip unexpected fields and sanitize types before they reach your model — especially for user-facing APIs where the input shape is entirely attacker-controlled.
