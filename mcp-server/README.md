# sebskills-mcp

An MCP server that exposes every skill in the parent `SEBSKILLS/skills/` tree
as:

- **One MCP prompt per skill** — direct invocation by name.
- **A `find_skill` tool** — keyword-ranked router that takes a free-form
  user intent and returns the best matches.
- **A `list_skills` tool** — flat (or category-filtered) catalogue.
- **A `skill://manifest` resource** — the full machine-readable index.

It reads `SKILL.md` frontmatter at startup. Skills with enriched frontmatter
(`when_to_use`, `when_not_to_use`, `similar_to`, `keywords`) rank more
accurately than skills with only the legacy `name` + `description` fields.

## Install / run

```bash
cd mcp-server
npm install
npm run build
```

Then register with an MCP client. For Claude Desktop, add to
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sebskills": {
      "command": "node",
      "args": ["/Users/seb.duffy/Documents/GitHub/SEBSKILLS/mcp-server/dist/index.js"]
    }
  }
}
```

For Claude Code, add to `~/.claude/mcp.json` (or use `claude mcp add`).

## Ranking

Pure keyword/token matching, no embeddings. Each skill scores by:

- +10 if its name appears literally in the query
- +3 per `keywords` hit
- +1 per ≥3-char token that appears in `name`, `description`,
  `when_to_use`, or `keywords`
- −0.5 per token that appears in `when_not_to_use` (the
  "use X instead" disambiguator)

When the top two scores are within 3 points, `find_skill` flags the result
as ambiguous so the calling agent knows to ask the user.

## Adding a new skill

Just drop a `SKILL.md` in `skills/<category>/<skill-name>/`. The server
re-loads on restart.
