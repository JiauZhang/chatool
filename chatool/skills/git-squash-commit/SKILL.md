---
name: git-squash-commit
description: Squash all commits from commitA to commitB into a single commit
parameters:
  - name: commitA
    type: string
    description: The earlier commit hash (exclusive start of range)
    required: true
  - name: commitB
    type: string
    description: The later commit hash (inclusive end of range)
    required: true
  - name: message
    type: string
    description: Commit message for the new squashed commit
    required: true
---

# Squash Commit Range

Squashes all commits **after `commitA` up to and including `commitB`** into a single, new commit.

## Usage

```bash
bash scripts/squash-commit.sh <commitA> <commitB> "<message>"
```

- commitA – start of range (excluded)
- commitB – end of range (included)
- message – **(required)** the commit message for the squashed commit
