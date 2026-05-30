---
alwaysApply: true
---

# Agent Rules

## Don'ts

- **No hardcoded paths.** Pass paths via arguments or config, never embed them in code.
- **No legacy code.** Do not keep backward-compatible branches, fallback defaults, or version adapters.

## Style

- No unnecessary comments or docstrings. Good code explains itself.
- All code content (variables, functions, classes, comments if any) in English only.

## Testing

- Tests must be written synchronously with code, not deferred.
- Before fixing a bug, first write a test that reproduces it.
- Before adding a feature or refactoring, first define the expected behavior as tests.
- Test coverage must anticipate edge cases, not just happy paths.
- Any code change (refactor, bugfix, feature) without corresponding test changes is incomplete.
