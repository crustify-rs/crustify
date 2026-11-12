---
name: audit-workflow
description: "How an audit of an existing Rust crate proceeds: its review waves, scope and results. Read before running an audit campaign."
---

# Audit workflow

An audit campaign hunts undefined behaviour reachable from safe code in a Rust repository,
especially a crate that wraps C, and, when the `equivalence` instrument is selected,
functional drift between the safe wrapper and the C library it binds. It needs no earlier
Crustify campaign: the target is any repository. It runs the same review batches a translation
campaign does, and each files a report and a reproducer for every finding it
confirms.

## 1. Running one

The settings are filled from
[`CRUSTIFY.template.md`](../../../templates/audit/CRUSTIFY.template.md), and kept in the
reviewed crate's repository as `crustify/CRUSTIFY.md`; a headless run needs every mandatory
answer. A later session in the repository resumes the audit. The ablation control, a bare
agent given only the task, is [`BARE.md`](../../../templates/audit/BARE.md)'s.

## 2. Setup

An audit runs the [setup workflow](../setup/SKILL.md), with two differences in its Builds:

- the configuration is the one that covers the most of the crate, typically every feature
  that builds on the platform: Cargo features, targets, `cfg`s and the C sources the build
  script compiles. A defect in a file no build compiles cannot be reproduced, and no scan
  sees it, so the files no variant compiles are recorded in the dashboard as
  unaudited; and
- the `coverage` variant is built only when `test-adequacy` is among the review objectives, and
  each sanitizer variant only when its sanitizer is selected. Miri and `equivalence` need
  no build.

The variants are rebuilt after a review wave whose batches changed the Rust or C sources.

## 3. Objectives

The settings' task objectives map onto review objectives:

| task objective | review objectives |
|---|---|
| `audit` | `ub`, `contracts`, `equiv` when `equivalence` is selected, and `disclose` |
| `revisit` | `revisit` and `disclose`, over the reports the task names or every report filed so far |
| `fix` | adds `fix` to the batches of `audit` and `revisit` |

A task selects `audit`, `revisit` or both, and `fix` optionally; review objectives the
settings name replace this mapping.

## 4. Worksets

For `audit`, the crate is divided into disjoint worksets of modules, one per review batch,
from the crate and the reports filed so far, in the order the tool skills' Audit workflow
sections give.

A batch spans around the settings' `max-loc` lines of code, 500 by default; a small margin
either way keeps a type with its impls, or avoids a small remainder. A module too large for
one batch is split by naming the types, trait impls and free functions each batch reviews
in it, so that each falls in exactly one batch. A type covers its fields and inherent impls
only; its trait impls are named in `trait_impls`, `<trait> for <type>` as their impl headers
spell them, with the type's batch unless they are worth a batch of their own. The methods
of an impl are never named as functions.

For `revisit`, the reports are divided into their own batches, grouped so that reports
needing the same instrument or the same build share a batch.

Each round of review batches, as many as [`concurrency`](../../operations/concurrency/SKILL.md) describes, is
one review wave: a wave of no link unit or module, each of its batches a `review` batch
holding its `paths` or `reports`. `schedule.json` does not record an audit's review waves:
each batch's `task.json` is its record.

## 5. Review waves

An audit's review waves are laid out as [`versioning`](../../operations/versioning/SKILL.md) and
[`layout`](../../operations/layout/SKILL.md) describe. Before
each, the settings are reread and their changes applied, and the agent memory every agent
reads at startup is curated. Each review batch's `task.json` holds its workset, its
objectives, its batch fields, its review wave branch and its run fields, as
[`task-schema`](../../artifacts/task-schema/SKILL.md)'s Review batches section describes,
with a `null` `link_unit` and `module`. The wave's batches run concurrently.

Each reviewer lands its reports and fixes on the review wave branch as
[`versioning`](../../operations/versioning/SKILL.md)'s Landing section describes. A reviewer that fails keeps its branch and
worktree for inspection; it is respawned, or its failure reported, and its workset is not
reviewed outside an agent unless the user asks for it. Once the wave has landed, its tip is
promoted to the working branch, and the shipping branch follows it with the user's
approval.

## 6. Spending

The settings set a maximum spend. Before each reviewer launches, the cost of every usage
record the audit has written is added up; once the total reaches the maximum, no further
reviewer launches, the running ones land, and the dashboard states that the budget was
reached.

## 7. Disclosure

Before the audit ends, its reports and disclosure notices are checked for consistency and
for claims they cannot support, its reproducers for soundness, and each notice against
[`reviewing`](../../verification/reviewing/SKILL.md)'s Disclosure section. No API key appears in a core dump
or any other reproducer artifact: the audit tree may be published.

## 8. Output

Each reviewer files its findings under its reviews dir, `crustify/reviews/waves/<batch id>/`. With
`disclose`, every finding carries a `disclosure.md` ready to send to the project's
maintainers. After the last review wave, the dashboard summarizes the reports, by default
`crustify/artifacts/audit-dashboard.md` from
[`dashboard.template.md`](../../../templates/audit/dashboard.template.md), in its format
exactly. It keeps the approved scope of instruments and bug classes, and marks a selected
instrument that was unavailable as untested, never as clean.
