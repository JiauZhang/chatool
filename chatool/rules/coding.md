---
alwaysApply: true
name: "coding-rule"
description: "General coding rules."
---

# Coding Rules

## Don'ts

- **No hardcoded paths.** Pass paths via arguments or config, never embed them in code.
- **No legacy code.** Do not keep backward-compatible branches, fallback defaults, or version adapters.

## Style

- No unnecessary comments or docstrings. Good code explains itself.
- All code content (variables, functions, classes, comments if any) in English only.

## Testing

- Tests must be written synchronously with code, not deferred.
- Before adding a feature or refactoring, first define the expected behavior as tests.
- Test coverage must anticipate edge cases, not just happy paths.
- Any code change (refactor, bugfix, feature) without corresponding test changes is incomplete.

## Debugging

- **Reproduce before fix.** Write a failing test first. Fix is done when test passes.
- **Bisect to find cause.** Remove code until the bug disappears. Don't guess.
- **One variable per attempt.** Change exactly one thing per try for clean attribution.
- **Compare, don't isolate.** List what differs between working and failing. The difference is the clue.
- **Fix cause, not symptom.** Post-hoc cleanup means root cause is still there. Remove it directly.
