---
title: "OpenAPI spec: the minimum you need to write and what it unlocks."
description: "OpenAPI specs enable auto-generated docs, client SDK generation, and request validation. Here's the minimum viable spec and what you get from writing it."
pubDate: 2024-06-24
tags: ["REST API", "Swagger"]
draft: false
---

OpenAPI (formerly Swagger) is a specification format for describing REST APIs. A spec is a YAML or JSON file that defines your endpoints, request parameters, request bodies, and response shapes. Writing one is optional, but it unlocks several things that would otherwise require manual effort.

## What you get from a spec

- **Interactive documentation** via Swagger UI or Redoc — users can try endpoints from the browser
- **Client SDK generation** — tools can generate typed clients in TypeScript, Python, Go, etc.
- **Server-side validation** — middleware can validate incoming requests against the spec automatically
- **Contract testing** — verify that your API matches its spec in CI

None of these require changing your application code. The spec is a separate description of what your API does.

## The minimum viable spec

An OpenAPI 3.0 spec has three required fields: `openapi`, `info`, and `paths`.

```yaml
openapi: 3.0.3
info:
  title: My API
  version: 1.0.0

paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: A list of users
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'

    post:
      summary: Create a user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserInput'
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationError'

  /users/{id}:
    get:
      summary: Get a user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: The user
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '404':
          description: User not found

components:
  schemas:
    User:
      type: object
      required: [id, email, name, createdAt]
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        name:
          type: string
        createdAt:
          type: string
          format: date-time

    CreateUserInput:
      type: object
      required: [email, name, password]
      properties:
        email:
          type: string
          format: email
        name:
          type: string
          minLength: 1
        password:
          type: string
          minLength: 8

    ValidationError:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: array
              items:
                type: object
                properties:
                  field:
                    type: string
                  message:
                    type: string
```

Save this as `openapi.yaml` in the root of your project.

## Using $ref to avoid repetition

The `$ref` syntax references a schema defined in `components/schemas`. Without it, you'd repeat the `User` object shape everywhere it appears. With it, you define it once and reference it across all endpoints. Changes to the shape propagate automatically.

## Adding authentication

If your API uses bearer tokens:

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: [] # applies globally

paths:
  /users/{id}:
    delete:
      security:
        - bearerAuth: [] # or per-endpoint
```

## Validating requests against the spec

The `express-openapi-validator` middleware reads your spec and validates incoming requests automatically:

```bash
npm install express-openapi-validator
```

```js
const OpenApiValidator = require('express-openapi-validator');

app.use(
  OpenApiValidator.middleware({
    apiSpec: './openapi.yaml',
    validateRequests: true,
    validateResponses: false, // enable in development to catch spec drift
  })
);
```

With this in place, any request that doesn't match the spec gets a 400 response before reaching your handlers. You can remove a lot of manual validation middleware if your spec is thorough.

## Generating client SDKs

With `openapi-generator-cli`:

```bash
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-fetch \
  -o ./client-sdk
```

This produces a typed TypeScript client from your spec. The same tool generates clients for Python, Java, Go, Ruby, and others.

## Where to start

Start with the spec for your most-used or most-documented endpoint. Fill in request/response schemas completely. Add the Swagger UI in the next step (covered in the next post). Once you see the interactive docs generated from the spec, the incentive to keep it up to date becomes self-reinforcing.

The spec is also a forcing function for consistent API design. Describing your API formally makes inconsistencies obvious in ways that reading the code doesn't.
