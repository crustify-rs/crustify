# Audit workflow

An audit campaign hunts undefined behaviour reachable from safe code in a Rust repository,
especially a crate that wraps C, and, when the `equivalence` instrument is selected,
functional drift between the safe wrapper and the C library it binds. It needs no earlier
Crustify campaign: the target is any repository. It runs the same reviewers a translation
campaign does, and each reviewer files a report and a reproducer for every finding it
confirms.

## 1. Running one

```sh
crustify /path/to/repo --settings /path/to/CRUSTIFY.md --model anthropic/claude-opus-5
```

The settings are filled from
[`CRUSTIFY.template.md`](../../templates/audit/CRUSTIFY.template.md); a headless run needs
every mandatory answer. Rerunning the command resumes the audit, and `--task-only` runs the
ablation control [`BARE.md`](../../templates/audit/BARE.md) describes.

## 2. Setup

An audit runs the [setup workflow](setup.md), with two differences in its Builds:

- the configuration is the one that covers the most of the crate, typically every feature
  that builds on the platform: Cargo features, targets, `cfg`s and the C sources the build
  script compiles. A defect in a file no build compiles cannot be reproduced, and no ffimap
  scan sees it, so the files no variant compiles are recorded in the dashboard as
  unaudited; and
- the `coverage` variant is built only when `coverage` is among the review objectives, and
  each sanitizer variant only when its sanitizer is selected. Miri and `equivalence` need
  no build.

The variants are rebuilt after a review wave whose reviewers changed the Rust or C sources.

## 3. Objectives

The settings' task objectives map onto the reviewer's objectives:

| task objective | reviewer objectives |
|---|---|
| `audit` | `ub`, `contracts`, `equiv` when `equivalence` is selected, and `disclose` |
| `revisit` | `revisit` and `disclose`, over the reports the task names or every report filed so far |
| `fix` | adds `fix` to the batches of `audit` and `revisit` |

A task selects `audit`, `revisit` or both, and `fix` optionally; review objectives the
settings name replace this mapping. Without `fix`, reviewers change nothing but their
reviews dirs.

## 4. Worksets

For `audit`, the crate is divided into disjoint worksets of modules, one per review batch,
from the crate and the reports filed so far. The modules that hold the smells the ffimap
skill names are batched first.

A batch spans around the settings' `max-loc` lines of code, 500 by default; a small margin
either way keeps a type with its impls, or avoids a small remainder. A module too large for
one batch is split by naming the types, trait impls and free functions each batch reviews
in it, so that each falls in exactly one batch. A type covers its fields and inherent impls
only; its trait impls are named in `trait_impls`, `<trait> for <type>` as their impl headers
spell them, with the type's batch unless they are worth a batch of their own. The methods
of an impl are never named as functions.

For `revisit`, the reports are divided into their own batches, grouped so that reports
needing the same instrument or the same build share a reviewer.

Each round of reviewers, up to the configured concurrency, is one review wave.

## 5. Review waves

An audit's review waves sit directly under the campaign, as
[`../layout.md`](../layout.md) describes. Before each, the settings are reread and their
changes applied, and the agent memory every agent reads at startup is curated. Each review
batch's `task.json` holds its workset, its objectives, its review wave branch and the
model and billing, as [`../artifacts/task.md`](../artifacts/task.md) describes:

```json
{"objectives": ["ub", "equiv", "disclose"], "modules": ["src/frame.rs", "src/codec/"],
 "base_branch": "<review wave branch>", "model": "<model>", "billing": "<billing>"}
```

A part of a module names its types, trait impls and functions, and a revisit batch its
report dirs (the run fields are left out of these two examples):

```json
{"objectives": ["ub", "contracts", "disclose"], "modules": [{"path": "src/codec.rs", "types": ["Decoder"], "trait_impls": ["Drop for Decoder", "Iterator for Packets<'_>"], "functions": ["open_input"]}]}
{"objectives": ["revisit", "disclose", "fix"], "reports": ["crustify/reviews/<batch id>/ub_safe/<slug>"]}
```

`crustify spawn-reviewer --help` describes the batch, and a dry run lists the objectives it
resolves to and rejects any the reviewer's prompt and skills do not offer. The wave's
reviewers run concurrently, launched a moment apart so that no two share a timestamp:

```bash
crustify spawn-reviewer <batch worktree> <batch dir>/task.json --log-dir <batch dir>
```

Each reviewer lands its reports and fixes on the review wave branch as
[`../landing.md`](../landing.md) describes. A reviewer that fails keeps its branch and
worktree for inspection; it is respawned, or its failure reported, and its workset is not
reviewed outside an agent unless the user asks for it. Once the wave has landed, its tip is
promoted to the campaign branch.

## 6. Spending

The settings set a maximum spend. Before each reviewer launches, the cost of every usage
record the audit has written is added up; once the total reaches the maximum, no further
reviewer launches, the running ones land, and the dashboard states that the budget was
reached.

## 7. Disclosure

Before the audit ends, its reports and disclosure notices are checked for consistency and
for claims they cannot support, its reproducers for soundness, and each notice against
[`../reviewing.md`](../reviewing.md)'s Disclosure section. No API key appears in a core dump
or any other reproducer artifact: the audit tree may be published.

## 8. Output

Each reviewer files its findings under its reviews dir, `crustify/reviews/<batch id>/`. With
`disclose`, every finding carries a `disclosure.md` ready to send to the project's
maintainers. After the last review wave, the dashboard summarizes the reports, by default
`crustify/artifacts/audit-dashboard.md` from
[`dashboard.template.md`](../../templates/audit/dashboard.template.md), in its format
exactly. It keeps the approved scope of instruments and bug classes, and marks a selected
instrument that was unavailable as untested, never as clean.
