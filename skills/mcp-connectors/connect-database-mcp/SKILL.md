---
name: connect-database-mcp
category: mcp-connectors
description: >
  Wire a SQL database into Claude Code over MCP for safe, read-only querying — Postgres, MySQL,
  SQLite, BigQuery (and 20+ more) via the googleapis MCP Toolbox for Databases (`toolbox`). Use when
  someone says "let Claude query my database", "connect Postgres to Claude", "add a MySQL/BigQuery MCP
  server", "read-only SQL access for the agent", "introspect my schema", or "run SELECTs against prod
  safely". Ships the guardrail recipe (least-privilege read-only role + SELECT-only tools.yaml) so the
  agent can explore schemas and run SELECTs but physically cannot INSERT/UPDATE/DELETE/DROP.
when_to_use:
  - "Let Claude run SELECT queries against my Postgres/MySQL/SQLite/BigQuery database"
  - "Connect my production database to Claude Code but block any writes"
  - "I want the agent to introspect the schema / list tables / describe columns"
  - "Add a database MCP server to Claude Code via stdio with env-var credentials"
  - "Give an analyst agent read-only SQL access to a warehouse (BigQuery/Snowflake)"
  - "Set up a locked-down tools.yaml with only whitelisted SELECT statements"
when_not_to_use:
  - "Connecting GitHub repos/issues/PRs — use connect-github-mcp"
  - "Generic 'how do I register any MCP server / scopes / .mcp.json' — use register-mcp-servers"
  - "Fetching/scraping web pages or HTML — use connect-web-fetch-scrape-mcp"
  - "Calling a REST/JSON HTTP API that isn't a database — use connect-public-api"
  - "Building your own MCP server from scratch — use the mcp-builder skill"
keywords: [database mcp, postgres mcp, mysql mcp, sqlite mcp, bigquery mcp, read-only sql, toolbox, mcp-toolbox, genai-toolbox, tools.yaml, schema introspection, execute_sql, list_tables, --prebuilt, stdio, least privilege, snowflake, sql server, guardrails, claude mcp add]
similar_to: [connect-github-mcp, register-mcp-servers, connect-web-fetch-scrape-mcp, connect-public-api]
inputs_needed:
  - Database engine + version (postgres | mysql | sqlite | bigquery | other)
  - Connection details (host, port, database name) OR SQLite file path OR GCP project id
  - Credentials for a READ-ONLY role (create one if it doesn't exist — see Recipe 0)
  - Config scope: local (this project only) vs user (all projects)
produces: An MCP server registered in Claude Code (.mcp.json / user config) exposing read-only schema + SELECT tools over the target database
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Connect a Database over MCP (read-only, guardrailed)

Give Claude Code the ability to explore a schema and run `SELECT`s against Postgres / MySQL /
SQLite / BigQuery — without the power to mutate data. Built on **MCP Toolbox for Databases**
(`googleapis/mcp-toolbox`, formerly `genai-toolbox`), a single Go binary called `toolbox`.

**Core safety principle: guardrails are enforced at the database, not by prompting.** The agent
will happily send whatever SQL it wants. The only reliable block on writes is a **least-privilege
read-only DB role** (Recipe 0). Layer a SELECT-only `tools.yaml` on top for defence in depth.

## When to use

Use for any "let the agent query my DB" request where you want schema introspection + SELECTs and
zero write risk. For non-DB HTTP APIs use `connect-public-api`; for generic MCP registration
mechanics (scopes, `.mcp.json`) use `register-mcp-servers`.

## Prerequisites

- **Claude Code CLI** (`claude mcp ...`) — check with `claude --version`.
- **The `toolbox` binary** (v1.6.0+). Install one way:
  ```bash
  # Homebrew (macOS/Linux)
  brew install mcp-toolbox

  # or direct binary (macOS Apple Silicon shown; swap darwin/arm64 for your platform)
  export VERSION=1.6.0
  curl -L -o toolbox "https://storage.googleapis.com/mcp-toolbox-for-databases/v$VERSION/darwin/arm64/toolbox"
  chmod +x toolbox && sudo mv toolbox /usr/local/bin/    # linux/amd64, windows/amd64.exe also available
  ```
  Verify: `toolbox --version`.
- A reachable database and, ideally, a **read-only role** (create in Recipe 0).
- **BigQuery only:** `gcloud auth application-default login` (ADC) + a GCP project id.

> Alternative binary transports: `docker run ... us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:$VERSION`,
> or `npx -y @toolbox-sdk/server ...`. The `claude mcp` recipes below assume a local `toolbox` binary; swap `command`/`args` for docker/npx if you prefer.

## Recipe 0 — Create a read-only role (DO THIS FIRST)

This is the guardrail. Everything else is convenience.

**Postgres:**
```sql
CREATE ROLE claude_ro LOGIN PASSWORD 'CHANGE_ME';
GRANT CONNECT ON DATABASE mydb TO claude_ro;
GRANT USAGE ON SCHEMA public TO claude_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO claude_ro;  -- future tables
```
Optionally cap runaway queries: `ALTER ROLE claude_ro SET statement_timeout = '30s';`

**MySQL:**
```sql
CREATE USER 'claude_ro'@'%' IDENTIFIED BY 'CHANGE_ME';
GRANT SELECT ON mydb.* TO 'claude_ro'@'%';
FLUSH PRIVILEGES;
```

**SQLite:** there is no role system — enforce read-only at connect time (Recipe 3).

**BigQuery:** grant the service account / user `roles/bigquery.dataViewer` (+ `bigquery.jobUser` to run
queries). No write/DML roles.

## Recipe 1 — Fastest: prebuilt read-only Postgres

`--prebuilt postgres` exposes generic tools (`list_tables`, `execute_sql`, plus schema/diagnostic
tools like `list_schemas`, `list_indexes`, `list_active_queries`). `execute_sql` will run *any* SQL —
which is exactly why you point it at the `claude_ro` role from Recipe 0, so writes fail with a
permission error at the DB.

```bash
claude mcp add-json postgres-ro '{
  "command": "toolbox",
  "args": ["--prebuilt", "postgres", "--stdio"],
  "env": {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DATABASE": "mydb",
    "POSTGRES_USER": "claude_ro",
    "POSTGRES_PASSWORD": "CHANGE_ME"
  }
}'
```

Swap `postgres` → `mysql` / `sqlite` / `bigquery` and use that engine's env prefix:
- **MySQL:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
- **SQLite:** `SQLITE_DATABASE` (path to `.db` file) — see Recipe 3 for true read-only
- **BigQuery:** `BIGQUERY_PROJECT` (uses ADC for auth)

Add `--scope user` to the `claude mcp add-json` command to make it global instead of project-local.

## Recipe 2 — Locked-down production: SELECT-only tools.yaml

The strongest posture: **no `execute_sql` at all.** You hand the agent a fixed menu of named,
parameterised SELECT tools. It can only call those. Combine with the `claude_ro` role for belt-and-braces.

`tools.yaml`:
```yaml
sources:
  pg:
    kind: postgres
    host: 127.0.0.1
    port: 5432
    database: mydb
    user: claude_ro
    password: ${POSTGRES_PASSWORD}   # env interpolation; never hard-code secrets

tools:
  list-tables:
    kind: postgres-sql
    source: pg
    description: List all tables and their comments.
    statement: |
      SELECT table_name, obj_description(('"'||table_name||'"')::regclass) AS comment
      FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;

  describe-table:
    kind: postgres-sql
    source: pg
    description: Show columns and types for one table.
    parameters:
      - name: table_name
        type: string
        description: Table to describe.
    statement: |
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns
      WHERE table_schema='public' AND table_name = $1 ORDER BY ordinal_position;

  search-orders:
    kind: postgres-sql
    source: pg
    description: Recent orders for a customer email.
    parameters:
      - name: email
        type: string
        description: Customer email.
    statement: SELECT id, total, created_at FROM orders WHERE customer_email = $1 ORDER BY created_at DESC LIMIT 100;

toolsets:
  readonly:
    - list-tables
    - describe-table
    - search-orders
```
Register it (env-substituted secret stays out of the file and out of `.mcp.json`):
```bash
export POSTGRES_PASSWORD='CHANGE_ME'
claude mcp add-json db-readonly '{
  "command": "toolbox",
  "args": ["--tools-file", "/ABS/PATH/tools.yaml", "--stdio"],
  "env": {"POSTGRES_PASSWORD": "'"$POSTGRES_PASSWORD"'"}
}'
```
Because every statement is a fixed `SELECT`, there is no surface for INSERT/UPDATE/DROP even if the
role were misconfigured. This is the recommended pattern for anything touching prod.

## Recipe 3 — SQLite, truly read-only

SQLite has no roles, so make the *connection* read-only. Easiest: the OS-level guarantee is a
`file:...?mode=ro&immutable=1` DSN, but the prebuilt takes a plain path. Two reliable options:

1. **tools.yaml with a read-only DSN** (preferred):
   ```yaml
   sources:
     lite:
       kind: sqlite
       database: "file:/ABS/PATH/app.db?mode=ro"
   ```
2. **Filesystem enforcement:** point at a copy and `chmod 444 app.db` so writes fail at the OS.

Then register with `--tools-file` as in Recipe 2, or use `--prebuilt sqlite --stdio` with
`SQLITE_DATABASE=file:/ABS/PATH/app.db?mode=ro`.

## Verify

```bash
# 1. Binary resolves and version is >= 1.6.0
toolbox --version

# 2. Config parses & the server boots without registering (Ctrl-C after "Server ready")
toolbox --tools-file /ABS/PATH/tools.yaml --port 5000            # or: toolbox --prebuilt postgres
#   -> then hit the local UI to sanity-check tools:
toolbox --tools-file /ABS/PATH/tools.yaml --ui                    # opens an inspector at 127.0.0.1:5000

# 3. Claude sees the server + tools
claude mcp list                       # server shows "connected"
claude mcp get postgres-ro            # inspect the registered entry
```
In a Claude session, ask it to "list the tables" then "SELECT count(*) from <table>". Then prove the
guardrail: ask it to `DELETE FROM <table>` or `DROP TABLE` — it must come back with a **permission
denied** (Recipe 0/1) or **no such tool** (Recipe 2), not a success.

## Pitfalls

- **Prebuilt `execute_sql` is NOT read-only by itself.** It runs any SQL. Read-only comes *only* from
  the `claude_ro` role (Recipe 0) or from dropping `execute_sql` entirely (Recipe 2). Never point
  `--prebuilt` at a superuser/owner account and call it "safe".
- **Secrets leaking into `.mcp.json`.** `claude mcp add-json` with an inline password writes it to a
  file that may be committed. Prefer `${VAR}` interpolation in `tools.yaml` and pass the value via
  `env`, or use `--scope local` and gitignore `.mcp.json`.
- **`--prebuilt` requires `--stdio` for Claude Code.** Without `--stdio` the binary starts an HTTP
  server (port 5000) that stdio-based MCP clients can't attach to.
- **Repo/name churn:** `genai-toolbox` was renamed to `googleapis/mcp-toolbox`; the binary is still
  `toolbox`. Docs live at googleapis.github.io/genai-toolbox and mcp-toolbox.dev. Prebuilt tools are
  pre-1.0 — tool names can shift between versions; pin your `VERSION`.
- **BigQuery costs.** A read-only role still lets the agent run expensive scans. Set a project/user
  **maximum bytes billed** or query quotas; `dataViewer` doesn't cap spend.
- **No query timeout = a stuck agent.** Set `statement_timeout` (Postgres) / `max_execution_time`
  (MySQL) on the read-only role so a runaway `SELECT` can't hang the session.
- **Reference `@modelcontextprotocol/server-postgres` / `-sqlite` are archived.** They still work for
  quick local demos but are unmaintained; prefer `toolbox` for anything ongoing.
- **Absolute paths only** for `--tools-file` and SQLite `database:` — Claude Code's cwd is not stable
  across tool calls.
