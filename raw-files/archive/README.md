# Archive

Skills that were previously in the framework but have been superseded or deprecated. **Not auto-loaded by Claude** — kept here for reference and potential re-promotion.

| Archived skill | Superseded by | Reason |
|---|---|---|
| `writing-skills` | [`skills/building-agents/skill-creator`](../../skills/building-agents/skill-creator) | Overlapping triggers caused ambiguous skill selection. `skill-creator` covers creation + editing + evals + description optimization with a richer, more trigger-friendly description and official Anthropic tooling (`eval-viewer/`). The TDD-for-skills material from `writing-skills` (especially `testing-skills-with-subagents.md`) remains valuable reference reading and can be consulted manually. |

## Resurrecting an archived skill

```bash
git mv raw-files/archive/<skill> skills/<category>/<skill>
```

Then re-add its row to the root `README.md` and the category `README.md`.
