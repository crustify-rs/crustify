---
name: audit-workflow
description: "How an audit of an existing Rust crate proceeds: its settings, objectives, scope and priority, worksets, review waves, crate pass, spending guard, consolidation and results. Read before running an audit campaign."
---

# Audit workflow

An audit campaign reviews a Rust repository that Crustify did not generate, especially a
crate that wraps C, for every objective [`reviewing`](../../verification/reviewing/SKILL.md)
offers that applies to it, undefined behaviour reachable from safe code first. It needs no
earlier Crustify campaign: the target is any repository. It runs the same review batches a
translation campaign does, each filing a report and a reproducer for every finding it
confirms, and it files nothing upstream: its reports, reproducers and disclosure drafts
are the user's to send.

## 1. Running one

The settings are filled from
[`CRUSTIFY.template.md`](../../../templates/audit/CRUSTIFY.template.md), and kept in the
reviewed crate's repository as `crustify/CRUSTIFY.md`; a headless run needs every mandatory
answer. A later session in the repository resumes the audit. The ablation control, a bare
agent given only the task, is [`BARE.md`](../../../templates/audit/BARE.md)'s.

## 2. Setup

An audit runs the [setup workflow](../setup/SKILL.md), with these differences in its Builds:

- the configuration is the one that covers the most of the crate, typically every feature
  that builds on the platform: Cargo features, targets, `cfg`s and the C sources the build
  script compiles. A defect in a file no build compiles cannot be reproduced, so the files
  no variant compiles are recorded in the dashboard as unaudited;
- the C library each variant links, the crate's bundled one or the system's, and its
  version, are recorded with the variant, since a finding's conditions name them; and
- the `coverage` variant is built only when `test-adequacy` is among the review objectives, and
  each sanitizer variant only when its sanitizer is selected. Miri and `equivalence` need
  no build.

The variants are rebuilt after a review wave whose batches changed the Rust or C sources.
An audit has no modules, dependencies or schedule artifacts.

## 3. Objectives

Every review objective can be run in an audit. The settings select them:

| objective | in an audit | selected by |
|---|---|---|
| `ub` | the safe interface, the unsafe interface within its obligations, and the exports the crate defines for C | `review-objectives` |
| `contracts` | the `# Safety` obligations and `// SAFETY:` justifications of the crate's unsafe code | `review-objectives` |
| `equiv` | the wrapper against the C it binds, where the raw bindings reach that C | `review-objectives`, with the `equivalence` instrument |
| `logic`, `unsafety`, `ergonomics`, `misc` | as in any review | `review-objectives` |
| `idiom` | a crate that ports C | `review-objectives` |
| `conventions`, and a tool's objectives | a Crustify-generated crate, or one the tool holds state for | `review-objectives` |
| `test-adequacy` | fills the gaps with tests in the crate's own suites, and needs the `coverage` variant | `review-objectives`, by name only |
| `revisit` | the reports the settings name, or every report filed so far | `tasks` |
| `disclose` | every report worth sending | `disclosure` |
| `fix` | what `audit` confirms and `revisit` still reproduces | `tasks` |

The default `review-objectives`, `all`, is every objective of the first six rows that
applies to the crate; an answer that names objectives runs those alone. `tasks` selects
`audit`, `revisit` or both: an `audit` batch carries the selected objectives, a `revisit`
batch `revisit`, and each of them `disclose` and `fix` as their answers say.

The `instruments` answer bounds the evidence, not the objectives: a UB or broken-contract
candidate is proved under Miri or a selected sanitizer, an `equiv` one under `equivalence`,
and the others by a Rust assertion, which needs none. A selected instrument that is
unavailable leaves what only it decides untested, never clean, and the instrument scope
is never broadened without the user.

## 4. Scope and priority

What an audit reviews, and in what order, is decided by reading the crate:

1. its public API surface under the audited configuration: every item a consumer can
   reach, re-exports, feature-gated items and trait impls included;
2. its unsafe code: every `unsafe` block, function, trait and impl;
3. its FFI seam: the raw bindings it calls, the pointers, strings, buffers and lengths
   that cross it, and each hand-off of ownership to or from C;
4. its `Send` and `Sync` impls, hand-written or inferred for a type that holds C state,
   against the C library's threading contract;
5. the lifetimes on its handles: borrowed handles, views and iterators, against their
   owners and the points at which C frees or invalidates what they borrow;
6. its callbacks: trampolines, user data, panics and reentrancy, and a callback that
   outlives its registration; and
7. its hand-written teardown and copies, and the exports it defines for C.

The modules where the safe public API reaches unsafe code or C with values, lifetimes or
threads a consumer controls come first, the rest of the unsafe code next, and the code
that reaches neither last, for the objectives that need no unsafe code. Every file a
variant compiles falls in a workset, or is listed in the dashboard as not reviewed, with
the reason. The dashboard's Scope records each workset's priority and the reading it
rests on, so that the plan can be checked and resumed.

A tool's output is a hint to this reading, as the tool's skill describes: it orients the
reading and cross-checks its inventory, and never decides what is in scope, what comes
first or what is left out. The plan is made the same way with no tool installed, with a
partial scan, or when the settings' `tool-hints` answer is `no`. Where a tool and the
source disagree, the source decides, the audit goes on, and the disagreement is proposed
as the tool's defect.

## 5. Worksets

For `audit`, the scope is divided into disjoint worksets, one per review batch, in the
priority order above, from the crate and the reports filed so far. Each is a `paths`
worklist. When the settings' `source` names an earlier revision as `since`, the scope is
what the crate's commits after it changed, and each workset a `commits` worklist of them.

A batch spans around the settings' `max-loc` lines of code, 500 by default; a small margin
either way keeps a type with its impls, or avoids a small remainder. A module too large for
one batch is split by naming the types, trait impls and free functions each batch reviews
in it, so that each falls in exactly one batch. A type covers its fields and inherent impls
only; its trait impls are named in `trait_impls`, `<trait> for <type>` as their impl headers
spell them, with the type's batch unless they are worth a batch of their own. The methods
of an impl are never named as functions.

For `revisit`, the reports are divided into their own batches, a `reports` worklist each,
grouped so that reports needing the same instrument or the same build share a batch.

Each round of review batches, as many as [`concurrency`](../../operations/concurrency/SKILL.md) describes, is
one review wave: a wave of no link unit or module, each of its batches a `review` batch.
`schedule.json` does not record an audit's review waves: each batch's `task.json` is its
record.

## 6. Review waves

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

### 6.1 Crate pass

Unless the settings' `crate-pass` answer is `no`, the last batch of the last review wave
is the crate pass, an audit's module pass: a `module_pass` batch with `wave_gates`, whose
`paths` are the crate's source and test roots, launched once every other batch has landed.
It reviews the crate whole, for what no workset shows alone, such as a thread-safety claim
against a path another module opens or a lifetime that crosses modules, and it runs the
crate's own test suites under Miri and each selected sanitizer, as
[`reviewing`](../../verification/reviewing/SKILL.md)'s Gates section describes a module's end.

## 7. Spending

The settings' `max-spend` caps what the audit of one crate spends: its reviewers, its
evolution reviews and the sessions that orchestrate it, priced as
[`accounting`](../../operations/accounting/SKILL.md)'s Cost and time section describes.
The total is taken before each launch and, while a wave runs, from the running agents'
transcripts as they grow.

A batch launches only while the total, what the running batches and it are expected to
cost, and a reserve for the consolidation and the dashboard stay within the maximum. A
batch is expected to cost the mean of those landed so far, and before any has landed the
estimate the brief states; the first wave is sized so too. Once no further batch fits, the
running ones land and the audit proceeds to its consolidation. A reviewer still running
when the total reaches the maximum is ended, its worktree kept and its batch recorded as
stopped at the budget.

The dashboard records the maximum, the total, whether the guard stopped the audit, and the
worksets it left unreviewed, in their priority order.

## 8. Consolidation

After the last review wave, and before anything is counted:

- the reports are merged by root cause, across batches, waves, objectives and instruments,
  as [`reviewing-reports`](../../verification/reviewing/reports/SKILL.md)'s Root causes
  section describes: those that share a cause become one report, in the earliest one's
  dir, with every site and the clearest reproducer, and the others' dirs are removed, the
  commit message naming each merge;
- the batches' notes are merged into the crate's one note, `crustify/reviews/notes.md`;
- each report's header is checked against its evidence: its class, its `aliasing-model
  only` or `unsettled` qualifier and its conditions;
- each reproducer is checked as a true proof of concept, as that skill's Reproducers
  section describes: one that is not goes to a `revisit` batch, or its report to the note
  as `unproven`; and
- each disclosure draft is checked against that skill's Disclosure section, its upstream
  check and status included, and for any claim its report does not support.

No API key appears in a core dump or any other reproducer artifact: the audit tree may be
published.

## 9. Output

Each reviewer files its findings under its reviews dir, `crustify/reviews/waves/<batch id>/`.
The dashboard summarizes them, by default `crustify/artifacts/audit-dashboard.md` from
[`dashboard.template.md`](../../../templates/audit/dashboard.template.md), in its format
exactly: one row per root cause once consolidated, with its class and its disclosure's
status, whose `REPORTED` and `FIXED` links fill the reported and fixed columns. It keeps
the approved scope of instruments and bug classes, and marks a selected instrument that
was unavailable as untested, never as clean.
