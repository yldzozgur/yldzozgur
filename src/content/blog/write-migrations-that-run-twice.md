---
title: "Write migrations that can run twice without breaking anything."
description: "Idempotent migrations don't fail if they've already been applied. This property makes deployments safer and CI pipelines more reliable."
pubDate: 2024-09-30
tags: ["Security"]
draft: false
---

A migration that fails because it already ran is worse than no migration at all — it blocks deployments and requires manual intervention. Writing idempotent migrations (ones that produce the same result whether run once or ten times) eliminates an entire category of deployment failures.

## Why migrations fail on re-run

A migration like this fails the second time:

```sql
ALTER TABLE users ADD COLUMN phone TEXT;
-- ERROR: column "phone" already exists
```

```sql
CREATE INDEX idx_users_email ON users (email);
-- ERROR: relation "idx_users_email" already exists
```

The SQL itself is correct — it's just not safe to run twice. Most migration tools (Flyway, Liquibase, Knex) track which migrations have run and skip them. But that tracking can fail — the tracking table gets corrupted, a migration partially ran, CI runs migrations from scratch, or you're setting up a new environment.

## Idempotent patterns

### ADD COLUMN

```sql
-- Not idempotent
ALTER TABLE users ADD COLUMN phone TEXT;

-- Idempotent
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
```

`IF NOT EXISTS` was added in PostgreSQL 9.6. For older versions:

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'phone'
  ) THEN
    ALTER TABLE users ADD COLUMN phone TEXT;
  END IF;
END $$;
```

### CREATE INDEX

```sql
-- Not idempotent
CREATE INDEX idx_users_email ON users (email);

-- Idempotent
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
```

For unique indexes:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users (email);
```

### CREATE TABLE

```sql
CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  user_id INT,
  action TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Upsert data

Seed data migrations often insert rows that should exist. Plain `INSERT` fails on duplicate:

```sql
-- Not idempotent
INSERT INTO roles (name) VALUES ('admin'), ('editor'), ('viewer');

-- Idempotent
INSERT INTO roles (name) VALUES ('admin'), ('editor'), ('viewer')
ON CONFLICT (name) DO NOTHING;
```

Or with update on conflict:

```sql
INSERT INTO settings (key, value)
VALUES ('max_upload_size', '10MB')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

### DROP and recreate (functions, views)

```sql
-- Idempotent: replaces if exists
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Idempotent: drop and recreate
DROP VIEW IF EXISTS active_users;
CREATE VIEW active_users AS
  SELECT * FROM users WHERE deleted_at IS NULL;
```

### ALTER TABLE RENAME COLUMN

There's no `IF EXISTS` for column renames. Use the check pattern:

```sql
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'full_name'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'display_name'
  ) THEN
    ALTER TABLE users RENAME COLUMN full_name TO display_name;
  END IF;
END $$;
```

## In Node.js migrations (Knex)

Knex provides schema builder methods that are idempotent by default for most operations:

```js
exports.up = async (knex) => {
  // hasTable check for table creation
  const exists = await knex.schema.hasTable("audit_log");
  if (!exists) {
    await knex.schema.createTable("audit_log", (table) => {
      table.increments("id");
      table.integer("user_id");
      table.text("action");
      table.timestamps(true, true);
    });
  }

  // hasColumn check for new columns
  const hasPhone = await knex.schema.hasColumn("users", "phone");
  if (!hasPhone) {
    await knex.schema.table("users", (table) => {
      table.string("phone").nullable();
    });
  }
};
```

## The CI benefit

Idempotent migrations let you run `migrate:latest` in CI without resetting the database first. If a test run partially applied migrations, the next run completes cleanly rather than failing on the already-applied steps. This also makes `docker-compose up` + migrations work predictably even when the database volume persists between runs.

One migration style to avoid: separate `up` and `down` functions that are never actually tested. Rollback migrations are valuable only if you test them. An idempotent `up` migration with no `down` is safer than a `down` migration that's never been run against real data.
