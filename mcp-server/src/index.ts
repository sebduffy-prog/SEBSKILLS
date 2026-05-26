#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import matter from "gray-matter";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILLS_ROOT = resolve(__dirname, "..", "..", "skills");

type Skill = {
  name: string;
  category: string;
  description: string;
  whenToUse: string[];
  whenNotToUse: string[];
  similarTo: string[];
  keywords: string[];
  inputsNeeded: string[];
  produces?: string;
  body: string;
  path: string;
};

const asStringArray = (v: unknown): string[] =>
  Array.isArray(v) ? v.map((x) => String(x)) : [];

function loadSkills(): Skill[] {
  const skills: Skill[] = [];
  const categories = readdirSync(SKILLS_ROOT, { withFileTypes: true }).filter(
    (d) => d.isDirectory(),
  );

  for (const cat of categories) {
    const catPath = join(SKILLS_ROOT, cat.name);
    let subdirs;
    try {
      subdirs = readdirSync(catPath, { withFileTypes: true }).filter((d) =>
        d.isDirectory(),
      );
    } catch {
      continue;
    }

    for (const sub of subdirs) {
      const skillPath = join(catPath, sub.name, "SKILL.md");
      let raw: string;
      try {
        raw = readFileSync(skillPath, "utf-8");
      } catch {
        continue;
      }
      const { data, content } = matter(raw);
      skills.push({
        name: String(data.name ?? sub.name),
        category: String(data.category ?? cat.name),
        description: String(data.description ?? ""),
        whenToUse: asStringArray(data.when_to_use),
        whenNotToUse: asStringArray(data.when_not_to_use),
        similarTo: asStringArray(data.similar_to),
        keywords: asStringArray(data.keywords),
        inputsNeeded: asStringArray(data.inputs_needed),
        produces: data.produces ? String(data.produces) : undefined,
        body: content,
        path: skillPath,
      });
    }
  }
  return skills;
}

const KEYWORD_HIT = 3;
const TOKEN_HIT = 1;
const NAME_HIT = 10;
const NOT_TO_USE_PENALTY = 0.5;
const AMBIGUITY_THRESHOLD = 3;
const MIN_TOKEN_LEN = 3;

function rankSkills(intent: string, skills: Skill[]) {
  const q = intent.toLowerCase();
  const tokens = q.split(/\W+/).filter((t) => t.length >= MIN_TOKEN_LEN);

  return skills
    .map((skill) => {
      const haystack = [
        skill.name,
        skill.description,
        ...skill.whenToUse,
        ...skill.keywords,
      ]
        .join(" ")
        .toLowerCase();
      const negHaystack = skill.whenNotToUse.join(" ").toLowerCase();

      let score = 0;
      if (q.includes(skill.name.toLowerCase())) score += NAME_HIT;
      for (const kw of skill.keywords) {
        if (q.includes(kw.toLowerCase())) score += KEYWORD_HIT;
      }
      for (const tok of tokens) {
        if (haystack.includes(tok)) score += TOKEN_HIT;
        if (negHaystack.includes(tok)) score -= NOT_TO_USE_PENALTY;
      }
      return { skill, score };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score);
}

const SKILLS = loadSkills();

const server = new McpServer({
  name: "sebskills",
  version: "0.1.0",
});

server.registerResource(
  "manifest",
  "skill://manifest",
  {
    title: "Skill manifest",
    description: "Machine-readable index of all available skills",
    mimeType: "application/json",
  },
  async () => ({
    contents: [
      {
        uri: "skill://manifest",
        mimeType: "application/json",
        text: JSON.stringify(
          SKILLS.map(({ body, path, ...rest }) => rest),
          null,
          2,
        ),
      },
    ],
  }),
);

server.registerTool(
  "find_skill",
  {
    description:
      "Find the best skill(s) for a user request. Returns ranked matches with confidence scores. If multiple skills are close in score, the response flags ambiguity so you can ask the user to choose.",
    inputSchema: {
      intent: z
        .string()
        .min(1)
        .describe("What the user wants to accomplish, in their own words"),
      category: z
        .string()
        .optional()
        .describe(
          "Optional category filter (e.g. ui-effects, documents, engineering-workflow)",
        ),
      limit: z
        .number()
        .int()
        .positive()
        .max(10)
        .optional()
        .describe("Max number of matches to return (default 5)"),
    },
    annotations: {
      readOnlyHint: true,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ intent, category, limit }) => {
    const max = limit ?? 5;
    const pool = category
      ? SKILLS.filter((s) => s.category === category)
      : SKILLS;
    const ranked = rankSkills(intent, pool).slice(0, max);

    if (ranked.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `No skills matched "${intent}". Use list_skills to browse the full catalogue.`,
          },
        ],
      };
    }

    const summary = ranked.map(({ skill, score }) => ({
      name: skill.name,
      category: skill.category,
      score: Number(score.toFixed(2)),
      summary: skill.description.split(/[.!?]/)[0] + ".",
      inputs_needed: skill.inputsNeeded,
      produces: skill.produces,
    }));

    const ambiguous =
      ranked.length > 1 &&
      ranked[0].score - ranked[1].score < AMBIGUITY_THRESHOLD;

    const guidance = ambiguous
      ? "\n\nAMBIGUOUS: Multiple skills match closely. Ask the user which one they want before proceeding."
      : "\n\nTo load the full skill, invoke the prompt with the matching name.";

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(summary, null, 2) + guidance,
        },
      ],
    };
  },
);

server.registerTool(
  "list_skills",
  {
    description:
      "List all available skills, optionally filtered by category. Useful when the user wants to browse rather than search.",
    inputSchema: {
      category: z.string().optional(),
    },
    annotations: {
      readOnlyHint: true,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ category }) => {
    const pool = category
      ? SKILLS.filter((s) => s.category === category)
      : SKILLS;
    const grouped = new Map<string, Skill[]>();
    for (const s of pool) {
      const list = grouped.get(s.category) ?? [];
      list.push(s);
      grouped.set(s.category, list);
    }
    const lines: string[] = [];
    for (const [cat, items] of [...grouped.entries()].sort()) {
      lines.push(`## ${cat}`);
      for (const s of items.sort((a, b) => a.name.localeCompare(b.name))) {
        const summary = s.description.split(/[.!?]/)[0];
        lines.push(`- **${s.name}** — ${summary}.`);
      }
      lines.push("");
    }
    return { content: [{ type: "text", text: lines.join("\n") }] };
  },
);

for (const skill of SKILLS) {
  server.registerPrompt(
    skill.name,
    {
      description: skill.description.slice(0, 200),
    },
    () => ({
      messages: [
        {
          role: "user",
          content: { type: "text", text: skill.body },
        },
      ],
    }),
  );
}

await server.connect(new StdioServerTransport());
