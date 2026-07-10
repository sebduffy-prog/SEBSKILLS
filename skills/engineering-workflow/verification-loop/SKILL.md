---
name: verification-loop
category: engineering-workflow
description: >
  A comprehensive verification system for Claude Code sessions.
when_to_use:
  - After completing a feature or significant code change
  - Before creating a PR, to confirm all quality gates pass
  - After refactoring, to verify nothing broke
  - During long sessions, as a continuous-mode checkpoint every 15 minutes or after major changes
  - When you want a structured verification report (build, types, lint, tests, security, diff)
when_not_to_use:
  - For a final done-check on task completion, use verification-before-completion instead
  - For diagnosing a specific failure rather than sweeping quality gates, use systematic-debugging
  - When only writing tests up front — that is test-driven-development / tdd-workflow territory
  - Immediate per-edit checks are better handled by PostToolUse hooks; this skill is the deeper review
keywords:
  - verification
  - quality gates
  - build check
  - type check
  - tsc
  - pyright
  - lint
  - ruff
  - test suite
  - coverage
  - security scan
  - secrets
  - console.log
  - diff review
  - verification report
  - pre-pr
  - continuous mode
  - hooks
similar_to:
  - verification-before-completion
  - systematic-debugging
  - requesting-code-review
  - tdd-workflow
inputs_needed:
  - Project build/test/lint commands (npm, pnpm, or Python equivalents)
  - Language/toolchain (TypeScript vs Python) to pick type-check and lint tools
  - The diff scope to review (e.g. git diff HEAD~1) and target coverage threshold (default 80%)
produces: A verification report (build/types/lint/tests/security/diff PASS-FAIL summary) with a READY/NOT READY verdict and issues to fix
status: stable
owner: seb.duffy
updated: 2026-07-10
origin: ECC
---

# Verification Loop Skill

A comprehensive verification system for Claude Code sessions.

## When to Use

Invoke this skill:
- After completing a feature or significant code change
- Before creating a PR
- When you want to ensure quality gates pass
- After refactoring

## Verification Phases

### Phase 1: Build Verification
```bash
# Check if project builds
npm run build 2>&1 | tail -20
# OR
pnpm build 2>&1 | tail -20
```

If build fails, STOP and fix before continuing.

### Phase 2: Type Check
```bash
# TypeScript projects
npx tsc --noEmit 2>&1 | head -30

# Python projects
pyright . 2>&1 | head -30
```

Report all type errors. Fix critical ones before continuing.

### Phase 3: Lint Check
```bash
# JavaScript/TypeScript
npm run lint 2>&1 | head -30

# Python
ruff check . 2>&1 | head -30
```

### Phase 4: Test Suite
```bash
# Run tests with coverage
npm run test -- --coverage 2>&1 | tail -50

# Check coverage threshold
# Target: 80% minimum
```

Report:
- Total tests: X
- Passed: X
- Failed: X
- Coverage: X%

### Phase 5: Security Scan
```bash
# Check for secrets
grep -rn "sk-" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
grep -rn "api_key" --include="*.ts" --include="*.js" . 2>/dev/null | head -10

# Check for console.log
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10
```

### Phase 6: Diff Review
```bash
# Show what changed
git diff --stat
git diff HEAD~1 --name-only
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Potential edge cases

## Output Format

After running all phases, produce a verification report:

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## Continuous Mode

For long sessions, run verification every 15 minutes or after major changes:

```markdown
Set a mental checkpoint:
- After completing each function
- After finishing a component
- Before moving to next task

Run: /verify
```

## Integration with Hooks

This skill complements PostToolUse hooks but provides deeper verification.
Hooks catch issues immediately; this skill provides comprehensive review.
