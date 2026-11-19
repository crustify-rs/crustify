---
name: layout
description: "What the .crustify/ dir at the repository's root holds: STATUS.md, REPORT.md, the reviews by kind, and scratch. Read before placing any of the port's own files."
---

# Layout

The port's own files, everything that is neither the C nor the Rust, sit under
`.crustify/` at the root of the C codebase's repository:

```text
.crustify/
├── STATUS.md                       progress per C file in scope, and the totals of time, tokens and cost
├── REPORT.md                       the final report
├── reviews/
│   └── <kind>/                     one dir per review objective: ub, contracts, equiv, logic, perf, …
│       ├── <component>-<n>.md      one finding
│       └── <component>-<n>/        its reproducer
└── tmp/                            scratch, gitignored
```

## 1. Reviews

Findings are grouped by their kind, the review objective that names them, as
[`reviewing`](../../verification/reviewing/SKILL.md) lists them, so that the author of the
next component reads every defect of a kind found so far in one place. A finding is never
deleted once filed: a later round updates its status in place.

## 2. Scratch

`.crustify/tmp/` is gitignored and holds anything residual: downloads, scratch builds and
experiments, intermediate outputs. Residual files go nowhere else in the repository. A
subagent's scratch is its own subdirectory, `.crustify/tmp/<agent>/`, never a directory the
host hands every agent of a session, where another agent can overwrite it.
