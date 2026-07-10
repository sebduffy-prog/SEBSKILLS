---
name: dockerfile-and-compose-authoring
category: devops
description: >-
  Author lean, secure Dockerfiles and Compose files and lint them with hadolint.
  Use to build multi-stage images, pick slim/distroless bases, run as a non-root
  user, order layers for cache hits, pin package versions, add HEALTHCHECKs, wire
  a .dockerignore, and write compose services with healthchecks + depends_on. Reach
  for this whenever a Dockerfile, docker-compose.yml, image bloat, or a hadolint
  DL/SC warning is in play.
when_to_use:
  - Writing or refactoring a Dockerfile from scratch and want it small and secure
  - Shrinking a bloated image with multi-stage builds and slim/distroless bases
  - Fixing hadolint warnings (DL3008 pin apt, DL3059 merge RUN, SC2086 quoting)
  - Adding a non-root user, HEALTHCHECK, or tight .dockerignore to an image
  - Writing a docker-compose.yml with healthchecks and ordered service startup
when_not_to_use:
  - Building Kubernetes manifests or Helm charts — use a k8s/helm skill
  - Provisioning cloud infra (VPC, IAM, buckets) — use terraform-iac-modules
  - Authoring CI that builds/pushes images — use github-actions-pipelines
  - Deploying an existing image to a PaaS — use the use-railway skill
keywords:
  - docker
  - dockerfile
  - compose
  - hadolint
  - multi-stage
  - distroless
  - non-root
  - healthcheck
  - layer-caching
  - dockerignore
  - slim
  - buildkit
  - oci
  - devops
similar_to:
  - github-actions-pipelines
  - terraform-iac-modules
  - incident-response-and-postmortem
inputs_needed: The app's language/runtime + build and start commands; the ports it listens on; any build-time vs runtime dependency split.
produces: A multi-stage Dockerfile, .dockerignore, optional docker-compose.yml, and a clean hadolint run.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Dockerfile & Compose Authoring

Build images that are **small, reproducible, non-root, and cache-friendly**, then
prove it with `hadolint`. Grounded against hadolint v2.14.0 and current BuildKit
behaviour.

## When to use

Any time you write or fix a `Dockerfile`, a `docker-compose.yml`, chase image
bloat, or resolve a hadolint `DL####`/`SC####` warning. Start from the recipe that
matches your runtime, adapt, then lint.

## Prerequisites

- **Docker** with BuildKit (default in Docker 23+). Confirm: `docker version`.
- **hadolint** for linting. No Homebrew on this Mac, so run it via Docker (no
  install needed):
  ```bash
  docker run --rm -i hadolint/hadolint:v2.14.0 < Dockerfile
  ```
  If you do have a local binary: `hadolint Dockerfile`.
- Know your app's **build command**, **start command**, and **listen port**.

## The 8 rules that matter

1. **Multi-stage**: build in a fat stage, copy only artifacts into a lean final stage.
2. **Pin the base tag** (`python:3.12-slim`, never `:latest`) — reproducibility (DL3007).
3. **Prefer `-slim` or distroless** final bases; alpine only if you accept musl quirks.
4. **Run as non-root** — create a user, `USER` before `CMD`.
5. **Order layers cache-cold→cache-hot**: deps manifest first, source last.
6. **One `RUN` per logical step**, chained with `&&`, cleaning caches in the same layer (DL3059).
7. **Pin package versions** where the linter asks (DL3008 apt, DL3018 apk, DL3013 pip).
8. **Ship a `.dockerignore`** so `.git`, `node_modules`, secrets never enter build context.

## Recipe A — Node.js (multi-stage, non-root, healthcheck)

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20.18-slim AS build
WORKDIR /app
# Copy manifests first so `npm ci` layer caches until deps change.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY . .
RUN npm run build

FROM node:20.18-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
# node:*-slim ships a pre-made non-root `node` user (uid 1000).
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
COPY --from=build --chown=node:node /app/package.json ./
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/server.js"]
```

## Recipe B — Python (slim, pinned pip, no cache)

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt .
# Build wheels once; --require-hashes if you have a locked file.
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=build /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
# Create a dedicated non-root user (DL3002).
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
```

## Recipe C — Go into distroless (tiny, no shell)

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# Static binary so it runs in a scratch/distroless image with no libc.
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app ./cmd/server

# distroless: no shell, no package manager, non-root by default.
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /app /app
EXPOSE 8080
# distroless has no shell, so HEALTHCHECK must exec the binary directly.
HEALTHCHECK --interval=30s --timeout=3s CMD ["/app", "-healthcheck"]
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

## The .dockerignore (ship this every time)

```gitignore
.git
.gitignore
**/node_modules
**/__pycache__
**/*.pyc
dist
build
.env
.env.*
*.log
Dockerfile
docker-compose*.yml
.DS_Store
```

## docker-compose.yml with healthchecks + ordered startup

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://app:app@db:5432/app
    depends_on:
      db:
        condition: service_healthy   # wait for db healthcheck, not just start
    restart: unless-stopped

  db:
    image: postgres:16.4-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

`condition: service_healthy` is the reliable way to order startup — plain
`depends_on` only waits for the container to *start*, not to be *ready*.

## Verify

```bash
# 1. Lint. Exit non-zero on warning+ so CI catches it.
docker run --rm -i hadolint/hadolint:v2.14.0 \
  --failure-threshold warning < Dockerfile

# 2. Build.
DOCKER_BUILDKIT=1 docker build -t myapp:test .

# 3. Confirm it runs as NON-root (must NOT print 0 / root).
docker run --rm myapp:test id -u        # distroless: skip, no shell

# 4. Check the image size — smaller is the goal.
docker images myapp:test --format '{{.Size}}'

# 5. Watch the healthcheck flip to healthy.
docker run -d --name t myapp:test && sleep 15 && \
  docker inspect --format '{{.State.Health.Status}}' t; docker rm -f t

# 6. Compose: validate + bring up.
docker compose config >/dev/null && docker compose up -d
```

### Tuning hadolint

Silence a rule you've consciously accepted with a repo-root `.hadolint.yaml`:

```yaml
ignored:
  - DL3008          # not pinning apt versions in a throwaway dev image
failure-threshold: warning
trustedRegistries:
  - docker.io
  - ghcr.io
```

Or inline, right above the offending line: `# hadolint ignore=DL3008,DL3009`.

## Pitfalls

- **`latest` base tags** (DL3007) — non-reproducible builds; pin a real version.
- **Secrets baked into layers** — `COPY .env` or `ARG TOKEN` used in a `RUN` leaves
  the value in history. Use BuildKit `--mount=type=secret` instead; never `ENV` a secret.
- **`apt-get` without `--no-install-recommends` + cache cleanup** — bloats the image.
  Do it in ONE layer: `RUN apt-get update && apt-get install -y --no-install-recommends foo=1.2 && rm -rf /var/lib/apt/lists/*`.
- **Cleaning in a separate `RUN`** — deletions in a later layer don't shrink earlier
  ones; the bytes are already committed. Clean in the same `RUN`.
- **`ADD` for local files** — use `COPY` (DL3020); `ADD` only for remote URLs/tar auto-extract.
- **Source copied before deps** — every code edit busts the dependency-install cache.
  Copy the manifest and install first, source last.
- **Shell-form HEALTHCHECK in distroless/scratch** — there's no `/bin/sh`, so
  `CMD curl ...` fails silently. Use exec form on the binary, or drop the healthcheck.
- **Running as root** (DL3002) — a container escape becomes host root. Always add `USER`.
- **Unquoted shell vars in `RUN`** (SC2086) — `rm -rf $DIR` word-splits; quote it.
