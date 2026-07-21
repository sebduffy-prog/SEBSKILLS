#!/usr/bin/env node
// Functional QA smoke test for a generated Recording Studio artist build.
// Checks structure only (build, leaked template strings, password/kicker wiring,
// audience<->CSV column coupling, stale data-source defaults) — NOT audience design,
// ideas content, or strategy prose. See ../qa-checklist.md.
//
// Usage:
//   node qa-smoke.mjs --old-artist "Muse" --artist "New Artist" --password "newpass" [--dir .] [--skip-build]

import { execSync } from "node:child_process";
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, relative, extname } from "node:path";

function parseArgs(argv) {
  const out = { dir: ".", skipBuild: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--old-artist") out.oldArtist = argv[++i];
    else if (a === "--artist") out.artist = argv[++i];
    else if (a === "--password") out.password = argv[++i];
    else if (a === "--dir") out.dir = argv[++i];
    else if (a === "--skip-build") out.skipBuild = true;
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
const ROOT = args.dir;
const results = []; // { section, status: 'PASS'|'WARN'|'FAIL', detail }
const record = (section, status, detail) => results.push({ section, status, detail });

function walk(dir, exclude, exts) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    if (exclude.includes(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) files.push(...walk(full, exclude, exts));
    else if (exts.includes(extname(entry))) files.push(full);
  }
  return files;
}

// --- 1. Build ---
if (!args.skipBuild) {
  try {
    execSync("npm run build", { cwd: ROOT, stdio: "pipe" });
    record("build", "PASS", "npm run build succeeded");
  } catch (e) {
    record("build", "FAIL", `npm run build failed:\n${e.stdout?.toString().slice(-1500) || e.message}`);
  }
} else {
  record("build", "WARN", "--skip-build set, not verified");
}

// --- 2. Leaked template-artist strings ---
if (args.oldArtist) {
  const scanDirs = ["components", "pages", "lib"].filter((d) => existsSync(join(ROOT, d)));
  const re = new RegExp(`\\b${args.oldArtist.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
  const hits = [];
  for (const d of scanDirs) {
    for (const f of walk(join(ROOT, d), ["node_modules", ".next"], [".js", ".jsx", ".ts", ".tsx"])) {
      const lines = readFileSync(f, "utf8").split("\n");
      lines.forEach((line, idx) => {
        if (re.test(line)) hits.push(`${relative(ROOT, f)}:${idx + 1}`);
      });
    }
  }
  if (hits.length === 0) record("leaked-artist-name", "PASS", `no "${args.oldArtist}" outside Market Research/ or public/`);
  else record("leaked-artist-name", "WARN", `${hits.length} hit(s) — review each (may be a legitimate default fallback, or a missed spot):\n  ` + hits.slice(0, 30).join("\n  "));
} else {
  record("leaked-artist-name", "WARN", "no --old-artist given, skipped");
}

// --- 3. Kicker string intact ---
{
  const KICKER = "VCCP Media Cultural Intelligence";
  const scanDirs = ["components", "pages"].filter((d) => existsSync(join(ROOT, d)));
  let found = false;
  for (const d of scanDirs) {
    for (const f of walk(join(ROOT, d), ["node_modules", ".next"], [".js", ".jsx", ".ts", ".tsx"])) {
      if (readFileSync(f, "utf8").includes(KICKER)) { found = true; break; }
    }
    if (found) break;
  }
  record("agency-kicker", found ? "PASS" : "FAIL", found ? `"${KICKER}" present` : `"${KICKER}" not found — do not rebrand the agency`);
}

// --- 4. Password wiring ---
{
  const indexFile = ["pages/index.jsx", "pages/index.js"].map((p) => join(ROOT, p)).find(existsSync);
  if (indexFile) {
    const src = readFileSync(indexFile, "utf8");
    const literals = [...src.matchAll(/pw\s*===\s*"([^"]+)"/g)].map((m) => m[1]);
    const defaults = ["muse2026"];
    const stillDefault = literals.some((l) => defaults.includes(l));
    if (stillDefault) {
      record("login-password", "FAIL", `login gate still accepts the template default password (${literals.join(", ")})`);
    } else if (args.password && !literals.includes(args.password)) {
      record("login-password", "FAIL", `login gate does not accept the configured password "${args.password}" (found: ${literals.join(", ") || "none"})`);
    } else if (literals.length === 0) {
      record("login-password", "WARN", "no literal password comparison found in pages/index — check manually");
    } else {
      record("login-password", "PASS", `login gate wired to non-default password (${literals.join(", ")})`);
    }
  } else {
    record("login-password", "WARN", "pages/index.jsx not found, skipped");
  }
}

// --- 5. Audience <-> CSV column coupling ---
{
  let audienceCount = null;
  const configCandidates = ["lib/artist.config.js", "lib/artist.config.mjs", "lib/artist.config.json"]
    .map((p) => join(ROOT, p)).filter(existsSync);
  if (configCandidates.length) {
    try {
      const src = readFileSync(configCandidates[0], "utf8");
      const m = src.match(/audiences\s*[:=]\s*\[([\s\S]*?)\]/);
      if (m) audienceCount = [...m[1].matchAll(/\{\s*["']?key["']?\s*:/g)].length;
    } catch { /* fall through to WARN below */ }
  }
  const mrDir = join(ROOT, "Market Research");
  if (audienceCount === null) {
    record("audience-csv-coupling", "WARN", "could not read audience segment count from lib/artist.config.* — check manually against qa-checklist.md §3");
  } else if (!existsSync(mrDir)) {
    record("audience-csv-coupling", "WARN", "no Market Research/ directory — awaiting-data build, nothing to check yet");
  } else {
    const csvs = readdirSync(mrDir).filter((f) => /^gwi_.*\.csv$/i.test(f));
    if (csvs.length === 0) {
      record("audience-csv-coupling", "WARN", "no gwi_*.csv files present — awaiting-data build");
    } else {
      const mismatches = [];
      for (const f of csvs) {
        const firstLine = readFileSync(join(mrDir, f), "utf8").split("\n").find((l) => l.trim().length > 0) || "";
        const cols = firstLine.split(",").length;
        const segmentCols = cols - 4; // question, name, metric, totals
        if (segmentCols !== audienceCount) mismatches.push(`${f}: ${segmentCols} value column(s), config has ${audienceCount} segment(s)`);
      }
      record("audience-csv-coupling", mismatches.length ? "FAIL" : "PASS",
        mismatches.length ? mismatches.join("\n  ") : `${csvs.length} CSV(s) match ${audienceCount} configured segment(s)`);
    }
  }
}

// --- Summary ---
const order = { FAIL: 0, WARN: 1, PASS: 2 };
results.sort((a, b) => order[a.status] - order[b.status]);
console.log("\nRecording Studio QA smoke — " + (args.artist || "(unnamed artist)") + "\n" + "=".repeat(60));
for (const r of results) {
  console.log(`[${r.status}] ${r.section}\n  ${r.detail}\n`);
}
const failCount = results.filter((r) => r.status === "FAIL").length;
const warnCount = results.filter((r) => r.status === "WARN").length;
console.log(`${failCount} fail, ${warnCount} warn, ${results.length - failCount - warnCount} pass.`);
console.log("Reminder: this checks structure only — audience design, ideas, and strategy content are not covered here.");
process.exit(failCount > 0 ? 1 : 0);
