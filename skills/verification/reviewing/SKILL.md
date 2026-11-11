---
name: reviewing
description: "How landed work is reviewed: tiered review batches and module passes, depth by how long code lasts, worklists, objectives, reports, reproducers, fixes, gates and plan corrections. Read before reviewing a batch, filing a finding or correcting an earlier plan."
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
lands on the same integration branch, as [`versioning`](../../operations/versioning/SKILL.md)
names it. The wave is promoted
once its translation batches and their reviews have landed. An audit's review waves are
[`audit-workflow`](../../workflows/audit-workflow/SKILL.md)'s.

Review is tiered. Each landing is reviewed within its wave, to the depth
[Depth](#11-depth) gives it. Before a module's integration in a port, and at its end in a
wrap, a module pass reviews the module whole, across its batches: its unsafe regions, its
exports and its tests. It is the last review batch of the module's last wave, marked
`module_pass`, launched once every other batch of that wave has landed; its worklist is
the module's paths, and it runs the wave's gates and the module's end gates, as
[Gates](#7-gates) describes.

Review batches are packed eagerly, as the batches they review land: one launches as soon as
the landed batches not yet reviewed fill it, and the last once every translation batch of
the wave has landed, so that review runs beside the wave's remaining batches rather than
after them. When a session runs only part of a wave, or part of the scope, its review
covers what it landed, before what consumes that starts.

A review batch takes the commits of translation batches of one route, `type` or `symbol`,
counted over their items: types and symbols are reviewed apart. It is larger than a
translation batch, since its reviewer reads landed code rather than writing it, and is
sized as [`scheduling`](../../planning/scheduling/SKILL.md)'s Batches section sizes one,
from what landed rather than what is planned: its lines, its unsafe sites and raw-pointer
positions, the regions it touches and the objectives it carries, without overwhelming its
reviewer, and within the settings' review caps (`id: review-workload`) when they set them.
A campaign may also review every translation batch on its own, with that batch's commits.

A review batch's `task.json` holds its worklist, its objectives, its wave branch and its
run fields, as [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Review batches section
describes. Without `objectives`, a batch runs every objective that applies: those this skill's
Objectives section and the tool skills describe.

### 1.1 Depth

How deeply a landing is reviewed follows how long its code lasts, as
[`testing`](../testing/SKILL.md)'s thoroughness does. A wrapper a port will replace, its
item's port planned in `schedule.json`, keeps its safe API through that port: it is
reviewed on its public API, for every objective that applies there, `ergonomics` included,
and not on its internals. An export is reviewed lightly while the C that calls it is
scheduled for porting, and thoroughly once it serves C that stays, for good or when a ship
point releases its module. Everything else is reviewed for every objective that applies.

## 2. Worklists

A review batch has one route:

| route | worklist | workset |
|---|---|---|
| `commits` | commits that translation batches landed | the code they add or change, and what it reaches |
| `paths` | source files and directories of a crate, or named types, trait impls and functions in one | everything they define, or the named parts |
| `reports` | none: the batch only revisits reports | the code the reports name |

A review batch's entry in `schedule.json` names the batches of its wave it
`reviews`, and each of those lists the `commits` it landed and the `items` it bound or
ported, whose `kind` gives their routes, `type` or `symbol`, as
[`task-schema`](../../artifacts/task-schema/SKILL.md)'s Routes section describes.

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
what the `unsafe` relies on. Contracts are judged by the side of the boundary they serve:
the gateways through which C reaches the crate, its `ffi_export` regions, and every other
unsafe code, which in a Crustify-generated crate sits in its `ffi_import` regions, whose
items are sound for every input their module can give them, as
[`binding`](../../rust/binding/SKILL.md)'s Safe boundary section requires.

### 3.3 UB (`ub`)

UB in the workset's API that its UB tests missed, by where it is reached from: the safe
public API, the unsafe public API within its `# Safety` obligations, or C through an
export within the C declaration's contract. The unsafe surface includes only the API the
workset adds; a workset that made no API item unsafe has none.

### 3.4 Equivalence (`equiv`)

Functional equivalence defects in the workset's API that its equivalence tests missed,
while the C it translates exists: in a port, until the module's integration. A divergence is a defect only when it is unintended: a doc comment, a `CHANGELOG`
entry, a named test asserting the new behaviour or a commit message explaining it marks it
deliberate, and one that corrects a C defect on purpose is no finding.

### 3.5 Logic (`logic`)

Behaviour that departs from the library's intended specification, in the workset's public
API or its private implementation, that its tests missed. The specification is, from the
most authoritative: the formats and standards the library implements, its documentation,
what its own test suites assert, and its maintainers' stated intent. A finding cites what
the behaviour departs from. Where the C departs from it too, the defect is not copied into
the Rust, and the finding records the C's. A leak, a deadlock or a panic on valid input
departs from nearly every specification.

### 3.6 Ergonomics (`ergonomics`)

Public API that is harder to use than it needs to be: its names, its conversions, its
iterators, builders or defaults where the C takes long argument lists, and the standard
traits its types lack. An item's safe API is fixed by the first batch that gives it one, a
wrap included, so its ergonomics are reviewed there.

### 3.7 Idiom (`idiom`)

Ported implementation that transliterates its C rather than using Rust's own means: index
loops where iterators fit, status codes where `Result` and `?` fit, lengths and releases
carried by hand where ownership carries them.

### 3.8 Conventions (`conventions`)

Deviations from the [conventions](../../rust/conventions/SKILL.md), in a Crustify-generated
batch only, unsafe code outside its regions included.

### 3.9 Misc (`misc`)

Any other defect in the workset.

### 3.10 Test adequacy (`test-adequacy`)

Gaps in the workset's tests: the C and Rust execution paths, and the states and
transitions, that the codebase's external and inline test suites leave unreached, found by
reading those suites against the code and measured as
[`testing-builds`](../testing/builds/SKILL.md)'s Coverage section describes; assertions too
weak to fail when the code is wrong; tests outside the suite of their kind; and the C test
cases none carries over. A gap is filled with tests, not filed: the coverage measurement
shows the delta.

### 3.11 Revisit (`revisit`)

The reports an earlier review filed, each rerun through its reproducer on the current
tree. One that still reproduces stays a finding of its objective; one that no longer does
has its report updated with the commit that changed the verdict; one that was never a
defect is removed, with the reason in the commit message.

### 3.12 Disclosure (`disclose`)

A `disclosure.md` beside each report that the user can send to the affected project's
maintainers unchanged: under 450 words, following the project's conventions for
disclosing security and UB issues, in an email-friendly format naming the maintainers when
it goes by email first. It includes a small snippet and the sanitizer crash or failing
assertion, offers the reproducer on request, and offers patches only under `fix`. It ends
with: `Found by [Crustify](https://github.com/crustify-rs/crustify), an experimental
UB/soundness auditing agent developed at UC Berkeley and running on <model name>, then
manually reviewed and independently reproduced.`

### 3.13 Fix (`fix`)

Whether a review patches what it finds. Without it, a review changes nothing outside
its reviews dir but the tests that fill the gaps `test-adequacy` finds.

## 4. Reports

A review batch files its findings under its reviews dir, as
[`layout`](../../operations/layout/SKILL.md)'s Reviews section spells it,
each in its own `<slug>` directory, holding its report and, when it has one, its
reproducer, in the sub-directory of its objective:

| objective | sub-directory |
|---|---|
| `unsafety` | `unsafe/` |
| `contracts`, of a gateway | `contracts/ffi_export/` |
| `contracts`, of other unsafe code | `contracts/ffi_import/` |
| `ub`, on the safe interface | `ub_safe/` |
| `ub`, on the unsafe interface | `ub_unsafe/` |
| `ub`, through an export | `ub_export/` |
| `equiv` | `equiv/` |
| `logic` | `logic/` |
| `ergonomics` | `ergonomics/` |
| `idiom` | `idiom/` |
| `conventions` | `conventions/` |
| `misc` | `misc/` |

A tool may add sub-directories for findings on its own output. A defect in a tool
rather than in the reviewed codebase, Crustify included, is no finding: it is a proposal,
with its reproducer, as [`evolution`](../../crustify/evolution/SKILL.md)'s Proposals
section describes.

A report states what is wrong, where, the evidence that proves it, and, under `fix`, how
it was fixed. It carries everything needed to rerun its reproducer from a clean checkout:
the exact command and the sanitizer output or failing assertion it produced. Neither a
report nor a reproducer carries an API key, in a core dump or anywhere else: a reviews dir
may be published.

## 5. Reproducers

A `ub`, `equiv` or `logic` candidate becomes a finding only once a reproducer proves it,
and so does a `contracts` candidate that claims a contract can be broken. A contract that merely
asks for more than the implementation needs, or a missing justification, is a finding
without one.

- A UB reproducer triggers one of the available sanitizers from Rust, and its report
  carries the sanitizer's trace. One targeting the safe public API carries
  `#[forbid(unsafe_code)]`; one targeting the unsafe API, or breaking a contract, honours
  the `# Safety` obligation. One reaching an export calls it as C would, through its raw
  binding, within the C declaration's contract.
- An equivalence reproducer fails one of [`testing`](../testing/SKILL.md)'s equivalence
  comparisons while running the raw C and the public Rust API, and its report carries the
  failing assertion. Once the C is gone, a behaviour finding is a `logic` one.
- A logic reproducer fails a Rust assertion of what the specification it cites requires,
  and its report carries the failing assertion.

Each reproducer is a standalone Cargo package: its `Cargo.toml` declares an empty
`[workspace]` table and depends on the affected crate through a relative `path`, and its
`src/main.rs` runs one scenario, so that running it exits non-zero on the affected commit.

## 6. Fixes

Under `fix`, every finding of the batch's objectives is patched:

- `unsafety`: the entry point is made safe;
- `contracts`: the `# Safety` obligation or `// SAFETY:` justification is corrected, or,
  when the contract can be broken, the code it guards, and the reproducer becomes a UB
  regression test;
- `ub`, `equiv` and `logic`: the defect is patched, and the reproducer becomes a
  regression test of the same kind, a UB test, an equivalence test or a unit test, on the
  side of the module it reaches. A UB
  regression test either runs without triggering a sanitizer, or fails to compile because
  the patch removed the safe path that reached the defect;
- `ergonomics`: the API is improved, and its consumers in the crate follow;
- `idiom`, `conventions` and `misc`: the transliteration, deviation or defect is fixed;
- `revisit`: every report that still reproduces is patched, as for its objective.

In a Crustify-generated batch, fixes follow the [conventions](../../rust/conventions/SKILL.md);
outside one, the repository's contributor instructions. Every test a review adds is classified as [`testing`](../testing/SKILL.md)
describes and placed where the conventions place tests of its kind, or, outside a
Crustify-generated batch, in the reviewed crate's own suite for that kind.

## 7. Gates

The gates [`testing-gates`](../testing/gates/SKILL.md)'s Regressions section gives a wave's
end run in its last review batch, which launches once every translation batch of the wave
has landed, and whose task's `wave_gates` says so: Miri in every wave. A module's end's,
every test under every available sanitizer and BSan over everything the module landed,
run in its module pass, when the wave is the module's last: no other translation wave in
`schedule.json` belongs to its module and runs after it. Each runs on the wave's tip
before any change, and again on the landed tree under `fix`. Without
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
