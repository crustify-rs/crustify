---
name: layout
description: "Where a port's own files sit: the crustify/ dir with STATUS.md, REPORT.md, the reviews dir and scratch. Read before placing any file that is not part of the Rust tree or the C."
---

# Layout

A port works in the repository of the C codebase it ports, beside the C, which stays where
it is so that what remains of it builds as before.

## 1. Tree

```text
<repository>/
├── …                   the C, as the codebase lays it out
├── <crate dir>/        the Rust crate, laid out as conventions describes
└── crustify/
    ├── STATUS.md       progress per C file in scope, and the totals of time, tokens and cost
    ├── REPORT.md       the final report
    ├── reviews/        every reviewer's report, with its reproducers
    ├── slow-tests      the tests the gates skip until a full run, as testing-gates describes
    └── tmp/            scratch, gitignored
```

The crate's directory is the agent's choice, such as `rust/`, one the C does not use; the
report names it. The C's build reaches the crate through its own build system, as
[`testing-builds`](../../verification/testing/builds/SKILL.md) describes. Paths into the C are relative to the repository's root, as the C lays itself
out. Nothing records a path to a scratch file.

## 2. Reviews

Each review's report sits at `crustify/reviews/<component>-r<round>.md`, its reproducers
in `crustify/reviews/<component>-r<round>/`, as
[`reviewing-reports`](../../verification/reviewing/reports/SKILL.md) lays them out. A
report is never deleted or rewritten once filed: a later round is a new file, so that the
next component's author can read every defect found so far.

## 3. Scratch

`crustify/tmp/` is gitignored and holds anything residual: downloads, scratch builds and
experiments, intermediate outputs. Residual files go nowhere else in the repository. A
subagent's scratch is its own subdirectory, `crustify/tmp/<agent>/`, never a directory the
host hands every agent of a session, where another agent can overwrite it.
