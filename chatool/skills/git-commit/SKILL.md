---
name: git-commit
description: 'Create conventional git commits with automatic type/scope detection from diff, intelligent staging, and interactive message generation. Triggered by "git commit" requests or "/git-commit".'
---

# Git Commit with Conventional Commits

## Overview

Create standardized, semantic git commits using the Conventional Commits specification. Analyze the actual diff to determine appropriate type, scope, and message.

**The commit message MUST be derived SOLELY from `git diff --staged` / `git diff`.** Do NOT use conversation history or memory of what was discussed. The diff is the ONLY source of truth.

## Conventional Commit Format

```
<type>[optional scope]: <description>
```

One line only. No body, no footer, no details.

## Commit Types

| Type       | Purpose                        |
| ---------- | ------------------------------ |
| `feat`     | New feature                    |
| `fix`      | Bug fix                        |
| `docs`     | Documentation only             |
| `style`    | Formatting/style (no logic)    |
| `refactor` | Code refactor (no feature/fix) |
| `perf`     | Performance improvement        |
| `test`     | Add/update tests               |
| `build`    | Build system/dependencies      |
| `ci`       | CI/config changes              |
| `chore`    | Maintenance/misc               |
| `revert`   | Revert commit                  |

## Breaking Changes

```
# Exclamation mark after type/scope
feat!: remove deprecated endpoint

# BREAKING CHANGE footer
feat: allow config to extend other configs

BREAKING CHANGE: `extends` key behavior changed
```

## Workflow

### 1. Analyze Diff

```bash
# If files are staged, use staged diff
git diff --staged

# If nothing staged, use working tree diff
git diff

# Also check status
git status --porcelain
```

### 2. Stage Files (if needed)

If nothing is staged or you want to group changes differently:

```bash
# Stage specific files
git add path/to/file1 path/to/file2

# Stage by pattern
git add *.test.*
git add src/components/*

# Interactive staging
git add -p
```

**Never commit secrets** (.env, credentials.json, private keys).

### 3. Generate Commit Message

Analyze the diff to determine:

- **Type**: What kind of change is this?
- **Scope**: What area/module is affected?
- **Description**: One concise sentence describing what changed (present tense, imperative mood, <72 chars). Describe the *result* (what was done), not the *process* (how it was done). No details, no body. Just the essence.

**Validate**: after writing, verify every part of the message corresponds to something visible in the diff. If not, rewrite.

### 4. Execute Commit

```bash
git commit -m "<type>[scope]: <description>"
```

## Best Practices

- One logical change per commit
- One sentence only — no body, no footer, no details
- Present tense: "add" not "added"
- Imperative mood: "fix bug" not "fixes bug"
- Keep under 72 characters

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (--force, hard reset) without explicit request
- NEVER skip hooks (--no-verify) unless user asks
- NEVER force push to main/master
- If commit fails due to hooks, fix and create NEW commit (don't amend)
