---
name: reviewing
description: "How landed work is reviewed: review batches, worklists, objectives, reports, reproducers, fixes, gates and plan corrections. Read before reviewing a batch, filing a finding or correcting an earlier plan."
---

# Reviewing

Review inspects work that has already landed, for a set of objectives, and files a report
for every defect it finds. In a translation campaign, reviewers inspect what each
translation batch landed before the waves that build on it start; in an audit, the modules of a crate
that Crustify did not generate (see [`audit-workflow`](../../workflows/audit-workflow/SKILL.md)); and planner runs review the
plan that earlier runs committed (see [Plan corrections](#9-plan-corrections)).

## 1. Review batches

When review is enabled, every translation batch's landing is reviewed before its wave is
promoted, so that no wave builds on unreviewed work. A review batch is a batch of the wave
it reviews, in `schedule.json`, that `reviews` some of its landed translation batches, and
lands on the same integration branch, never checked out, as
[`versioning`](../../operations/versioning/SKILL.md) names it. The wave is promoted
once its translation batches and their reviews have landed. An audit's review waves are
[`audit-workflow`](../../workflows/audit-workflow/SKILL.md)'s.

Review batches are packed eagerly, as the batches they review land: one launches as soon as
the landed batches not yet reviewed fill it, and the last once every translation batch of
the wave has landed, so that review runs beside the wave's remaining batches rather than
after them. When a session runs only part of a wave, or part of the scope, its review
covers what it landed, before what consumes that starts.

A review batch takes the commits of translation batches of one route, `type` or `symbol`,
counted over their items: types and symbols are reviewed apart. It is larger than a
translation batch, since its reviewer reads landed code rather than writing it: about
5-10x a type batch's items and 3-4x a symbol batch's, without overwhelming its reviewer,
and within the settings' review caps (`id: review-workload`) when they set them. A campaign
may also review every translation batch on its own, with that batch's commits.

A review batch's `task.json` ([`task-schema`](../../artifacts/task-schema/SKILL.md)) holds its worklist,
its objectives, its wave branch and its run fields:

```json
{"objectives": ["lifecycle", "unsafety", "ub", "equiv", "fix"], "commits": ["3f2a9c1", "8be04d7"],
 "wave": 8, "batch": 0, "link_unit": "<link unit>", "module": "<module name>", "foundational": false,
 "base_branch": "<wave branch>", "backend": "<backend>", "billing": "<billing>"}
```

Without `objectives`, a batch runs every objective its reviewer offers that applies.
`crustify spawn-reviewer --help` describes them, and a dry run lists those a batch
resolves to and rejects any the reviewer's prompt and tool specs do not offer.

## 2. Worklists

A review batch has one route:

| route | worklist | workset |
|---|---|---|
| `commits` | commits that translation batches landed | the code they add or change, and what it reaches |
| `paths` | source files and directories of a crate, or named types, trait impls and functions in one | everything they define, or the named parts |
| `reports` | none: the batch only revisits reports | the code the reports name |

A review batch's entry in `schedule.json` names the batches of its wave it
`reviews`, and each of those lists the `commits` it landed and the `items` it bound or
ported, whose `kind` gives their routes: `type` or `symbol`.

A module named with `types`, `trait_impls` or `functions` limits the workset to those: a
type with its fields and its inherent impls, wherever they are; a trait impl, named
`<trait> for <type>` as its header spells it, with its methods and associated items; a
free function with nothing else. What they call and what implements their traits is read,
but only the workset is reported on.

## 3. Objectives

Each objective names a kind of defect. A tool may contribute objectives of its own.

### 3.1 Unsafety (`unsafety`)

Unsafe annotations and raw pointers on the workset's public API that safe, idiomatic
variants could replace, so that API consumers write less unsafe code.

### 3.2 Contracts (`contracts`)

Safety contracts that are incorrect, incomplete or ambiguous:

- the `# Safety` obligation of a public entry point that must legitimately stay unsafe: a
  caller who honours it can still reach undefined behaviour, or it asks for something the
  implementation does not need;
- the `// SAFETY:` justification of an `unsafe` block: the invariant it claims does not
  hold on every path that reaches the block, or no comment justifies the block at all.

A contract is tested by trying to break it: an input, a call sequence or an interleaving
that honours the obligation, or reaches the block through safe code, and still violates
what the `unsafe` relies on.

### 3.3 UB (`ub`)

UB in the workset's public API that its UB tests missed. The unsafe surface includes only
the API the workset adds; a workset that made no API item unsafe has none.

### 3.4 Equivalence (`equiv`)

Functional equivalence defects in the workset's public API that its equivalence tests
missed. A divergence is a defect only when it is unintended: a doc comment, a `CHANGELOG`
entry, a named test asserting the new behaviour or a commit message explaining it marks it
deliberate, and one that corrects a C defect on purpose is no finding.

### 3.5 Internal (`internal`)

Defects in the workset's private implementation that its unit tests missed.

### 3.6 Conventions (`conventions`)

Deviations from the [conventions](../../rust/conventions/SKILL.md), in a Crustify-generated batch only.

### 3.7 Misc (`misc`)

Any other defect in the workset.

### 3.8 Coverage (`coverage`)

Gaps the codebase's existing external and inline test suites leave in the workset's C and
Rust execution paths, found by reading those suites against the C code and measured as
[`testing`](../testing/SKILL.md) describes. A gap is filled with tests, not filed: the coverage
measurement shows the delta.

### 3.9 Revisit (`revisit`)

The reports an earlier review filed, each rerun through its reproducer on the current
tree. One that still reproduces stays a finding of its objective; one that no longer does
has its report updated with the commit that changed the verdict; one that was never a
defect is removed, with the reason in the commit message.

### 3.10 Disclosure (`disclose`)

A `disclosure.md` beside each report that the user can send to the affected project's
maintainers unchanged: under 450 words, following the project's conventions for
disclosing security and UB issues, in an email-friendly format naming the maintainers when
it goes by email first. It includes a small snippet and the sanitizer crash or failing
assertion, offers the reproducer on request, and offers patches only under `fix`. It ends
with: `Found by [Crustify](https://github.com/crustify-rs/crustify), an experimental
UB/soundness auditing agent developed at UC Berkeley and running on <model name>, then
manually reviewed and independently reproduced.`

### 3.11 Fix (`fix`)

Whether the reviewer patches what it finds. Without it, a review changes nothing outside
its reviews dir but the tests that fill coverage gaps.

## 4. Reports

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`,
each in its own `<slug>` directory, holding its report and, when it has one, its
reproducer, in the sub-directory of its objective:

| objective | sub-directory |
|---|---|
| `unsafety` | `unsafe/` |
| `contracts` | `contracts/` |
| `ub`, on the safe interface | `ub_safe/` |
| `ub`, on the unsafe interface | `ub_unsafe/` |
| `equiv` | `equiv/` |
| `internal` | `internal/` |
| `conventions` | `conventions/` |
| `misc` | `misc/` |

A tool may add sub-directories for findings on its own output. A defect in a tool
rather than in the reviewed codebase is filed, with its reproducer, on a dedicated branch
and worktree of that tool's local checkout.

A report states what is wrong, where, the evidence that proves it, and, under `fix`, how
it was fixed. It carries everything needed to rerun its reproducer from a clean checkout:
the exact command and the sanitizer output or failing assertion it produced. Neither a
report nor a reproducer carries an API key, in a core dump or anywhere else: a reviews dir
may be published.

## 5. Reproducers

A `ub` or `equiv` candidate becomes a finding only once a reproducer proves it, and so
does a `contracts` candidate that claims a contract can be broken. A contract that merely
asks for more than the implementation needs, or a missing justification, is a finding
without one.

- A UB reproducer triggers one of the available sanitizers from Rust, and its report
  carries the sanitizer's trace. One targeting the safe public API carries
  `#[forbid(unsafe_code)]`; one targeting the unsafe API, or breaking a contract, honours
  the `# Safety` obligation.
- An equivalence reproducer fails one of [`testing`](../testing/SKILL.md)'s equivalence
  comparisons while running the raw C and the public Rust API, and its report carries the
  failing assertion.

Each reproducer is a standalone Cargo package: its `Cargo.toml` declares an empty
`[workspace]` table and depends on the affected crate through a relative `path`, and its
`src/main.rs` runs one scenario, so that `cargo run` exits non-zero on the affected commit.

## 6. Fixes

Under `fix`, every finding of the batch's objectives is patched:

- `unsafety`: the entry point is made safe;
- `contracts`: the `# Safety` obligation or `// SAFETY:` justification is corrected, or,
  when the contract can be broken, the code it guards, and the reproducer becomes a UB
  regression test;
- `ub`, `equiv` and `internal`: the defect is patched, and the reproducer becomes a
  regression test of the same kind: a UB test, an equivalence test, or a unit test. A UB
  regression test either runs without triggering a sanitizer, or fails to compile because
  the patch removed the safe path that reached the defect;
- `conventions` and `misc`: the deviation or defect is fixed;
- `revisit`: every report that still reproduces is patched, as for its objective.

Outside a Crustify-generated batch, fixes follow the repository's contributor
instructions. Every test a review adds is classified as [`testing`](../testing/SKILL.md)
describes and placed where the conventions place tests of its kind, or, outside a
Crustify-generated batch, in the reviewed crate's own suite for that kind.

## 7. Gates

The gates [`testing`](../testing/SKILL.md)'s Regressions section gives a wave run in its last
review batch, which launches once every translation batch of the wave has landed, and
whose task's `wave_gates` says so: Miri in
every wave, and BSan over everything the module landed when the wave is the module's last:
no other translation wave in `schedule.json` belongs to its module and runs after it. Both
run on the wave's tip before any change, and again on the landed tree under `fix`. Without
`fix`, each true positive a gate finds is filed as a UB report. A BSan report on an earlier
wave's items belongs to the last wave's review.

## 8. Landing

A review batch lands two commits, as [`versioning`](../../operations/versioning/SKILL.md)'s Landing section describes: first its
`crustify/reviews/` changes, so the reproducers run on the affected commit, then its
changes to the Rust tree, if any.

## 9. Plan corrections

A planner run that corrects what an earlier run decided files each correction as a finding
under `crustify/reviews/planner/`: `modules/` for `modules.json` and
`schedule.json`, and one sub-directory per tool artifact. Adding what the plan lacks,
updating it to the current schema, re-deriving entries under a rule that has changed and
re-planning the waves a change moves are no findings.

Each finding is its own `<slug>` directory, named for the finding
(`split-libavutil-hash`), never for the run, and never reused. Its `report.md` states:

- what the earlier plan decided, quoting the entries changed;
- the evidence against it: linker outputs, sources and tool queries, with the exact
  commands and paths to rerun them;
- the edit and what it moves downstream: modules, waves or batches, and the waves
  re-emitted; and
- any question only the user can answer.
