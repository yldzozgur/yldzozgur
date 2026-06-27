---
title: "Parameterized queries are the only SQL injection fix that works. No exceptions."
description: "SQL injection persists because developers reach for string sanitization instead of parameterized queries. Here's why sanitization fails and how parameters work at the driver level."
pubDate: 2024-07-25
tags: ["Security"]
draft: false
---

SQL injection has been in the OWASP Top 10 for two decades. It's not there because it's exotic — it's there because the broken pattern is easy to write and the correct pattern requires understanding why it works, not just what to type.

## The vulnerability, exactly

Unsafe code concatenates user input directly into a SQL string:

```js
// DO NOT DO THIS
app.get("/users/:id", async (req, res) => {
  const query = `SELECT * FROM users WHERE id = '${req.params.id}'`;
  const result = await db.query(query);
  res.json(result.rows);
});
```

A normal request with `id = 42` produces:
```sql
SELECT * FROM users WHERE id = '42'
```

An attacker sends `id = ' OR '1'='1`:
```sql
SELECT * FROM users WHERE id = '' OR '1'='1'
```

`'1'='1'` is always true. This returns every row in the users table.

A more dangerous payload for a login endpoint: `' OR '1'='1' --`

```sql
SELECT * FROM users WHERE email = '' OR '1'='1' --' AND password = '...'
```

The `--` comments out the password check. The attacker logs in as the first user in the database — usually an admin.

And the worst case, for databases that allow stacked queries or procedures:

```sql
'; DROP TABLE users; --
```

## Why sanitization doesn't work

The instinct to "sanitize input" by escaping or removing dangerous characters is fundamentally flawed. SQL injection is not a problem with bad characters — it's a problem with treating data as code.

Common sanitization approaches that fail:

**Blacklisting**: block `'`, `;`, `--`, `DROP`, `UNION`. Attackers use hex encoding, comment syntax variations, or whitespace tricks to bypass character-level filters. This is a cat-and-mouse game you will lose.

**Escaping user input manually**:
```js
// Still dangerous — custom escaping misses edge cases
const safeId = req.params.id.replace(/'/g, "''");
const query = `SELECT * FROM users WHERE id = '${safeId}'`;
```

Manual escaping depends on knowing every edge case for every database version. MSSQL, MySQL, PostgreSQL, and SQLite all have different escaping rules.

**Validating to a type**: `parseInt(req.params.id)` works for integer IDs. But this is only valid when the input is always a simple type, and it doesn't generalize.

## Parameterized queries: how they actually work

A parameterized query (also called a prepared statement) separates the SQL structure from the data completely. The query is sent to the database as a template with placeholders. The data is sent separately. The database driver handles the boundary — your code never constructs a SQL string with user data embedded.

```js
// PostgreSQL with node-postgres (pg)
app.get("/users/:id", async (req, res) => {
  const result = await db.query(
    "SELECT * FROM users WHERE id = $1",
    [req.params.id]
  );
  res.json(result.rows);
});
```

With MySQL/mysql2:
```js
const [rows] = await db.execute(
  "SELECT * FROM users WHERE id = ?",
  [req.params.id]
);
```

The database receives:
1. Query template: `SELECT * FROM users WHERE id = $1`
2. Parameter: `42`

The database parses the SQL structure first, then binds the parameter as data. There is no string concatenation. There is no parsing of the user's input as SQL. The malicious payload `' OR '1'='1` becomes a literal string being compared against the `id` column — it does not affect the query structure.

## Multiple parameters

```js
const result = await db.query(
  `SELECT * FROM posts
   WHERE author_id = $1
   AND published = $2
   AND created_at > $3
   ORDER BY created_at DESC
   LIMIT $4`,
  [userId, true, startDate, limit]
);
```

Each `$n` corresponds to the nth element in the parameters array. The parameter order in the array must match the placeholder order in the query. Node-postgres uses `$1`-style placeholders; mysql2 uses `?`.

## ORMs: parameterized by default

If you're using an ORM like Prisma, Sequelize, or TypeORM, parameterized queries are the default behavior for the query builder:

```js
// Prisma — parameterized automatically
const user = await prisma.user.findFirst({
  where: { email: req.body.email },
});

// Sequelize — parameterized automatically
const user = await User.findOne({
  where: { email: req.body.email },
});
```

The risk with ORMs is when you reach for raw queries to handle something the ORM can't express:

```js
// Dangerous even in Prisma
const result = await prisma.$queryRaw`
  SELECT * FROM users WHERE id = ${userId}
`;

// Safe — Prisma's tagged template literal parameterizes automatically
// But if you use $queryRawUnsafe with string concatenation, you're back to square one
await prisma.$queryRawUnsafe(`SELECT * FROM users WHERE id = ${userId}`);
// ^ NEVER do this
```

The rule is absolute: user input must reach the database as a parameter, never as part of the query string. No framework, no sanitization function, and no amount of careful escaping is a substitute.
