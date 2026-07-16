---
name: openapi-client-codegen
category: engineering-workflow
description: >-
  Generate a fully typed API client from an OpenAPI/Swagger spec with orval —
  TypeScript models, fetch/axios call functions, Zod request+response
  validators, React Query / SWR / Vue Query / Svelte Query hooks, and MSW mocks
  — all regenerated from the contract so the client can never drift. Reach for
  this the moment you would otherwise hand-write typed fetch wrappers, `any`-typed
  responses, or duplicate a backend's DTOs by hand in the frontend.
when_to_use:
  - You have an openapi.yaml/json (or Swagger URL) and need a typed TS client, not hand-rolled fetch
  - Frontend and backend keep drifting because request/response types are copied by hand
  - You want React Query / SWR / Vue / Svelte hooks generated per endpoint from the spec
  - You need runtime Zod validation of API responses at the boundary, derived from the schema
  - You want MSW handlers auto-generated from the spec to mock the API in tests/Storybook
when_not_to_use:
  - Designing or reviewing the OpenAPI contract itself — use api-contract-design
  - Generating a server/stubs or a non-JS client (Go, Python, Java) — use openapi-generator directly
  - Spec is GraphQL not OpenAPI — use graphql-codegen instead
  - You only need types and no runtime/hooks — openapi-typescript is lighter than orval
keywords:
  - openapi
  - swagger
  - orval
  - codegen
  - typescript
  - react-query
  - swr
  - zod
  - msw
  - api-client
  - fetch
  - axios
  - mutator
  - tags-split
  - contract
similar_to:
  - api-contract-design
  - repo-context-packer
  - dependency-upgrade-migration
inputs_needed: An OpenAPI 3.x / Swagger 2.0 spec (local .yaml/.json path or a URL), a Node project with a package manager, and a chosen client target (react-query | swr | vue-query | svelte-query | fetch | axios).
produces: Generated TS client under a target dir (models, endpoint functions, framework hooks), optional .zod.ts validators, optional MSW mock handlers, and an orval.config.ts wired to a package.json script.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# OpenAPI Client Codegen (orval)

Turn an OpenAPI/Swagger contract into a typed client that regenerates deterministically. One command produces models, per-endpoint call functions, framework data-fetching hooks, Zod validators, and MSW mocks. The generated dir is disposable — you never edit it, you edit the spec or the config and re-run.

## When to use

Use when a spec exists and you'd otherwise write typed `fetch` wrappers or copy DTOs. If the spec doesn't exist yet, stop and design it first (`api-contract-design`). For non-JS clients or server stubs, use `openapi-generator`; for types-only, `openapi-typescript` is lighter.

## Prerequisites

- **Node ≥ 18** and a package manager (npm/pnpm/yarn). macOS default `python3` is irrelevant here — this is a Node toolchain.
- **A valid spec.** Orval accepts OpenAPI 3.0/3.1 and Swagger 2.0, as a local `openapi.yaml`/`.json` or an `https://` URL.
- **Peer deps you actually use.** Orval only *generates* code; you install the runtime libs yourself: `@tanstack/react-query`, `swr`, `axios`, `zod`, `msw` as applicable.
- **No API keys.** Fully offline except when the input `target` is a remote URL.

```bash
npm i -D orval
# runtime libs for the target you pick (install only what you use):
npm i @tanstack/react-query zod
npm i -D msw
```

## Steps

### 1. Point orval at the spec (validate first)

```bash
# Sanity-check the spec resolves before generating:
npx orval --config ./orval.config.ts --watch=false 2>&1 | head -40
```

### 2. Author `orval.config.ts`

The config is a map of named projects. Each has `input` (the spec) and `output` (what to emit). This is the canonical React Query setup with split files, Zod, and MSW mocks:

```ts
// orval.config.ts
import { defineConfig } from 'orval';

export default defineConfig({
  api: {
    input: {
      target: './openapi.yaml',        // local path OR 'https://…/openapi.json'
      // validation: true,             // run the spec through @stoplight/spectral
    },
    output: {
      target: './src/api/generated',   // where endpoint code + hooks land
      schemas: './src/api/model',      // models in their own dir (keeps diffs clean)
      client: 'react-query',           // see enum below
      mode: 'tags-split',              // one folder per OpenAPI tag
      mock: true,                      // emit MSW handlers (getXHandler / getXMock)
      clean: true,                     // delete stale generated files each run
      prettier: true,                  // format output (needs prettier installed)
      override: {
        mutator: {                     // route every call through your fetch/axios instance
          path: './src/api/http-client.ts',
          name: 'customInstance',
        },
        query: { useSuspenseQuery: true },
      },
    },
  },
});
```

**`client` enum** (exact values): `react-query`, `swr`, `vue-query`, `svelte-query`, `angular`, `axios`, `axios-functions`, `fetch`, `zod`, `hono`, `effect`, `mcp`.

**`mode` enum**: `single` (one file), `split` (impl + schemas + mocks split), `tags` (one file per tag), `tags-split` (a folder per tag — best for large specs).

### 3. Provide the mutator (custom HTTP instance)

The mutator is where auth headers, baseURL, and error normalization live — the one file you *do* hand-write. Its signature must return the response `data`:

```ts
// src/api/http-client.ts
export const customInstance = async <T>(
  config: { url: string; method: string; params?: unknown; data?: unknown; headers?: HeadersInit; signal?: AbortSignal },
): Promise<T> => {
  const query = config.params
    ? '?' + new URLSearchParams(config.params as Record<string, string>)
    : '';
  const res = await fetch(`${import.meta.env.VITE_API_URL}${config.url}${query}`, {
    method: config.method,
    headers: { 'Content-Type': 'application/json', ...config.headers },
    body: config.data ? JSON.stringify(config.data) : undefined,
    signal: config.signal,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? (undefined as T) : res.json();
};
```

### 4. Generate

```bash
npx orval --config ./orval.config.ts
# iterate on the spec with live regen:
npx orval --config ./orval.config.ts --watch
```

Wire it into `package.json` so CI and teammates get identical output:

```jsonc
{ "scripts": { "api:gen": "orval --config ./orval.config.ts" } }
```

### 5. Use the generated hooks

```tsx
import { useListPets, useCreatePet } from '@/api/generated/pets/pets';

function Pets() {
  const { data, isLoading } = useListPets({ limit: 20 });
  const { mutate } = useCreatePet();
  // data is fully typed from the schema; no `any`
}
```

## Recipes

- **Runtime validation, separate files.** Add a second project that emits Zod without clobbering the client files:
  ```ts
  apiZod: {
    input: { target: './openapi.yaml' },
    output: { client: 'zod', target: './src/api/zod', fileExtension: '.zod.ts', mode: 'tags-split' },
  }
  ```
  Then validate at the boundary: `petSchema.parse(await res.json())`. Or set `override.zod.generate.response = true` on the main project to validate inside generated calls.

- **MSW mocks in tests.** With `mock: true`, orval emits `getPetsMock()` (faker-backed sample data) and MSW handlers. Register them: `setupServer(...getPetsMockHandler())` — great for Storybook and Vitest without a live backend.

- **SWR / Vue / Svelte.** Swap `client` to `swr`, `vue-query`, or `svelte-query`; the model + mutator layers are identical, only the hook wrappers change.

- **Split one spec into feature bundles.** Use `filters: { tags: ['pets'] }` under `output` to generate only a subset of tags per project.

## Verify

- **Generation is clean & deterministic.** `git status` after `npm run api:gen` shows only intended diffs; run twice — the second run is a no-op.
- **Types compile.** `npx tsc --noEmit` passes against the generated dir.
- **Contract drift is caught in CI.** Fail the build if regen changes anything:
  ```bash
  npm run api:gen && git diff --exit-code src/api || { echo 'API client out of date — run npm run api:gen'; exit 1; }
  ```
- **Mocks are valid.** MSW handlers register without throwing in a test setup file.

## Pitfalls

- **Never edit generated files.** They're overwritten (`clean: true` deletes them). Customize via `override`, the mutator, or the spec — not by hand.
- **`clean: true` deletes the whole `target` dir.** Point `target`/`schemas` at dedicated folders, never at a dir that also holds hand-written code.
- **Mutator must return `data`, not the raw Response.** Generated hooks expect the unwrapped payload; returning the `Response` object breaks every typed return.
- **Operationless endpoints get ugly names.** Missing `operationId` in the spec → orval invents verbose names from the path. Fix the spec upstream (`api-contract-design`), not the output.
- **Zod in `split`/`tags-split` has known codegen edge cases** (see orval issue #2933) — verify generated `.zod.ts` compiles; pin your orval version and re-check on upgrade.
- **`prettier: true` requires prettier installed**; otherwise output is unformatted and diffs get noisy. Alternatively format the target dir in a post-gen script.
- **Remote-URL inputs make generation non-hermetic.** For reproducible CI, vendor the spec into the repo and regenerate from the local file.
