---
name: api-contract-design
category: engineering-workflow
description: >-
  Design and lint a REST API contract properly — author OpenAPI 3.1 (JSON Schema
  2020-12) with reusable components, enforce house style with a custom Spectral
  ruleset (naming, kebab paths, required descriptions, operationId), standardise
  RFC 9457 problem+json error envelopes and cursor/offset pagination, then spin
  up a Prism mock server so consumers can build before the backend exists. Reach
  for this when writing, reviewing, or tightening an OpenAPI spec or its lint gate.
when_to_use:
  - Authoring a new OpenAPI 3.1 spec from scratch and wanting it right the first time
  - Adding a Spectral lint gate (CI or pre-commit) with custom house-style rules
  - Standardising error responses and pagination across many endpoints
  - Spinning up a mock server from a spec so frontend/consumers unblock early
  - Reviewing an existing spec for consistency, missing descriptions, or drift
when_not_to_use:
  - Generating a typed client/SDK from a finished spec — use openapi-client-codegen
  - Designing GraphQL or gRPC/protobuf contracts — Spectral/OpenAPI do not apply
  - Packing a whole repo into LLM context — use repo-context-packer
  - Structural find/replace across source files — use ast-grep-codemod
keywords:
  - openapi
  - openapi-3.1
  - spectral
  - prism
  - api-design
  - json-schema
  - rest
  - linting
  - mock-server
  - rfc9457
  - problem-json
  - pagination
  - error-envelope
  - contract-first
  - ruleset
  - operationid
similar_to:
  - openapi-client-codegen
  - repo-context-packer
  - ast-grep-codemod
  - changelog-release-automation
inputs_needed: An OpenAPI 3.1 spec (or intent to write one); Node.js for npx to run Spectral + Prism; optional existing house style/naming conventions to encode as rules
produces: A well-structured openapi.yaml, a custom .spectral.yaml ruleset, a passing lint report, reusable Problem+Pagination components, and a running Prism mock server URL
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# API Contract Design

Author a REST contract that is consistent, machine-lintable, and mockable before
a line of backend exists. Everything runs via `npx` — no global installs, no brew.

## When to use

Go contract-first: write OpenAPI 3.1, gate it with a Spectral ruleset encoding *your*
house style (not just defaults), bake in one error shape and one pagination shape, and
hand consumers a Prism mock. Pairs with `openapi-client-codegen` (consumes the spec).

## Prerequisites

- **Node.js 18+** — both tools are npx-only: `@stoplight/spectral-cli`, `@stoplight/prism-cli`. No API keys.
- **OpenAPI 3.1** aligns `type` with **JSON Schema 2020-12**: `examples` is an array, `nullable` is gone — use `type: [string, "null"]`.
- Spectral bundles `spectral:oas` (OpenAPI 2/3 structural rules); you `extends` it, then add house rules.
- Sanity-check the toolchain: `npx -y @stoplight/spectral-cli --version` and `npx -y @stoplight/prism-cli --version`.

## Recipe 1 — A well-formed OpenAPI 3.1 skeleton

Keep schemas in `components` and `$ref` them everywhere; every operation gets a unique
`operationId` (codegen and Spectral need it) and a real `description`.

```yaml
openapi: 3.1.0
info:
  title: Widgets API
  version: 1.0.0
  description: Manage widgets. Contract-first; mocked with Prism.
servers:
  - url: https://api.example.com/v1
paths:
  /widgets:
    get:
      operationId: listWidgets
      summary: List widgets
      description: Returns a cursor-paginated page of widgets.
      parameters:
        - $ref: '#/components/parameters/Cursor'
        - $ref: '#/components/parameters/Limit'
      responses:
        '200':
          description: A page of widgets.
          content:
            application/json:
              schema: { $ref: '#/components/schemas/WidgetPage' }
        '400': { $ref: '#/components/responses/Problem' }
    post:
      operationId: createWidget
      summary: Create a widget
      description: Creates a widget and returns it.
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/WidgetCreate' }
      responses:
        '201':
          description: Created.
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Widget' }
        '422': { $ref: '#/components/responses/Problem' }
components:
  parameters:
    Cursor: { name: cursor, in: query, required: false, description: Opaque cursor from a prior page's `nextCursor`., schema: { type: string } }
    Limit:  { name: limit,  in: query, required: false, description: Max items (1–100)., schema: { type: integer, minimum: 1, maximum: 100, default: 20 } }
  schemas:
    Widget:
      type: object
      required: [id, name, createdAt]
      properties:
        id: { type: string, format: uuid }
        name: { type: string, minLength: 1 }
        description: { type: [string, 'null'] }
        createdAt: { type: string, format: date-time }
    WidgetCreate:   # request body: Widget minus server-set fields
      type: object
      required: [name]
      properties:
        name: { type: string, minLength: 1 }
        description: { type: [string, 'null'] }
    WidgetPage:
      type: object
      required: [items, nextCursor]
      properties:
        items:
          type: array
          items: { $ref: '#/components/schemas/Widget' }
        nextCursor:
          type: [string, 'null']
          description: Cursor for the next page; null when no more pages.
    Problem:
      description: RFC 9457 problem detail.
      type: object
      required: [type, title, status]
      properties:
        type: { type: string, format: uri, default: 'about:blank' }
        title: { type: string }
        status: { type: integer }
        detail: { type: string }
        instance: { type: string, format: uri }
        # Extend with an `errors: [{ pointer, detail }]` array for per-field validation.
  responses:
    Problem:
      description: Error (RFC 9457).
      content:
        application/problem+json:
          schema: { $ref: '#/components/schemas/Problem' }
```

Two decisions worth copying: **one `Problem` schema** reused by every error, and
**cursor pagination** (`nextCursor: null` terminates), which scales better than offset.
For offset, expose `limit`/`offset` params plus a `total` field.

## Recipe 2 — A custom Spectral house-style ruleset

`extends` the built-in OAS rules, then add yours. `given` is JSONPath (the `~` suffix
selects the property *key*, needed for path casing). Built-in functions include
`truthy`, `pattern`, `length`, `casing`, `enumeration`, `alphabetical`, `schema`.

`.spectral.yaml`:

```yaml
extends: ['spectral:oas']
rules:
  # Enforce our own rules on top of the defaults
  paths-kebab-case:
    description: Paths must be kebab-case with optional {params}.
    severity: error
    given: $.paths[*]~
    then:
      function: pattern
      functionOptions:
        match: '^(\/|[a-z0-9-]+|{[a-zA-Z0-9_]+})+$'

  operation-operationId-required:
    description: Every operation needs an operationId.
    severity: error
    given: $.paths[*][get,put,post,delete,patch]
    then: { field: operationId, function: truthy }

  operationId-camelCase:
    description: operationId must be camelCase.
    severity: error
    given: $.paths[*][get,put,post,delete,patch].operationId
    then:
      function: casing
      functionOptions: { type: camel }

  operation-description-required:
    description: Every operation needs a description.
    severity: warn
    given: $.paths[*][get,put,post,delete,patch]
    then: { field: description, function: truthy }

  error-uses-problem-json:
    description: 4xx/5xx responses must use application/problem+json.
    severity: error
    given: $.paths[*][*].responses[?(@property.match(/^(4|5)/))].content
    then: { field: application/problem+json, function: truthy }

  no-inline-request-schemas:
    description: Request bodies must $ref a component, not inline the schema.
    severity: warn
    given: $.paths[*][post,put,patch].requestBody.content[*].schema
    then: { field: '$ref', function: truthy }
```

Run the gate (disable a rule with `rulename: off`; prefer fixing over suppressing):

```bash
npx -y @stoplight/spectral-cli lint openapi.yaml --ruleset .spectral.yaml
# CI: fail only on errors (not warn/info), machine-readable output
npx -y @stoplight/spectral-cli lint openapi.yaml --fail-severity error --format json -o report.json
```

## Recipe 3 — Mock server from the spec

Prism serves the spec as a live HTTP server. Static mode returns the schema's
`examples`; `--dynamic` (`-d`) generates fresh schema-valid data each call.

```bash
npx -y @stoplight/prism-cli mock openapi.yaml -p 4010              # static examples
npx -y @stoplight/prism-cli mock openapi.yaml -p 4010 --dynamic    # random valid data
curl -s localhost:4010/widgets | head
curl -s localhost:4010/widgets -H 'Prefer: code=400'              # force a status
```

Prism also **validates requests** — a bad body returns 422 problem+json, so
consumers get contract feedback for free.

## Verify

```bash
# 1. Structurally valid + passes house rules (exit 0 = clean)
npx -y @stoplight/spectral-cli lint openapi.yaml --ruleset .spectral.yaml --fail-severity error
echo "spectral exit: $?"
# 2. Mock boots and serves a documented route
npx -y @stoplight/prism-cli mock openapi.yaml -p 4010 &  PRISM=$!
sleep 4; curl -sf localhost:4010/widgets >/dev/null && echo "mock OK"; kill $PRISM
```

## Pitfalls

- **3.0 vs 3.1 drift.** `nullable: true` and singular `example` are 3.0. In 3.1 use `type: [string, 'null']` and `examples: [ ... ]`. Set `openapi: 3.1.0` and Spectral's oas rules will flag mismatches.
- **Missing operationId.** Codegen (`openapi-client-codegen`) derives function names from it; without it names are ugly and unstable. The ruleset above makes it an error.
- **JSONPath `~` confusion.** `$.paths[*]` selects path *objects*; `$.paths[*]~` selects the path *string* — you need the `~` form for path-casing rules.
- **`--fail-severity` matters in CI.** By default Spectral exits non-zero on any `warn`. Set `--fail-severity error` so `info`/`warn` guidance doesn't block merges (or promote a rule to `error` when you mean it).
- **Prism static mode needs examples.** With no `examples` in a schema, static mode may return sparse/empty bodies — use `--dynamic` or add `examples`. Errors must be `application/problem+json`, not `application/json`, or the `error-uses-problem-json` rule (and consumers) break.
