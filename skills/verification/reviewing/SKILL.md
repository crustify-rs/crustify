---
name: reviewing
description: "How a port's components are reviewed: independent review rounds until one finds nothing new, learning from earlier reports, worksets, depth, objectives, fixes and gates; reviewing-reports gives the reports and reproducers. Read before reviewing a component, briefing a reviewer, or fixing what a review found."
---

# Reviewing

Review inspects a component that has been ported, for a set of objectives, and files a
report of every defect it finds, as [`reviewing-reports`](reports/SKILL.md) describes. The
reviewer is a subagent that wrote none of the code it reviews.

## 1. Rounds

Every component is reviewed before the components that build on it start, so that no
work builds on unreviewed code. A round reviews the component's code as merged, or as its
author proposes to merge it, and files one report, `crustify/reviews/<component>-r<round>.md`,
as [`layout`](../../operations/layout/SKILL.md)'s Reviews section places it.

Review runs in rounds until one finds nothing new:

1. The reviewer reviews the component for every objective that applies.
2. The author fixes every finding, as [Fixes](#4-fixes) describes, and runs the gates.
3. The next round's reviewer reruns every earlier finding's reproducer, as
   [Revisit](#311-revisit) describes, and reviews what the fixes changed and what the
   earlier rounds left out.

The rounds end when a round finds no new defect against the objectives and every earlier
finding is fixed or recorded as deliberately left, with its reason. A finding left open
is named in the report.

Review is tiered. Beside each component's rounds, the whole port gets crate-wide passes
before the report: its unsafe regions, its exports, its public Rust API and its tests,
across components, since a defect may sit between two components each reviewed alone.

### 1.1 Learning from earlier reports

Before a component is written, its author reads the reports on the components before it.
Before a round, its reviewer reads them too, and checks the component for every class of
defect they found: a class found once is looked for everywhere after. A defect a reviewer
finds in one component is then looked for in the components already merged, by its
author or by a review of its own, and every new site joins the finding's report. A
report is never rewritten to hide a defect; a later round's verdict is a file of its own.

### 1.2 Depth

How deeply a component is reviewed follows how long its code lasts. An export is
reviewed lightly while the C that calls it is still to be ported, and thoroughly once it
serves C that stays. Everything else is reviewed for every objective that applies.

## 2. Worksets

A round's brief names its workset:

| workset | what it covers |
|---|---|
| a component | the code its commits add or change, and what it reaches |
| paths | source files and directories, or named types, trait impls and functions |
| reports | the code earlier reports name, for a round that only revisits them |

A workset named by types, trait impls or functions is limited to those: a type with its
fields and its inherent impls, wherever they are; a trait impl, named `<trait> for <type>`
as its header spells it, with its methods and associated items; a free function with
nothing else. What they call and what implements their traits is read, but only the
workset is reported on.

A workset is reviewed from its source, to the depth [Depth](#12-depth) gives it. What a
tool lists of it shows where the reading may start and cross-checks what the reading
found; it never bounds the review, and code no tool flagged is reviewed all the same.

## 3. Objectives

Each objective names a kind of defect. A round's brief may narrow them; without that, a
round runs every objective that applies. A tool may contribute objectives of its own.

### 3.1 Unsafety (`unsafety`)

Unsafe annotations and raw pointers on the workset's public API that safe, idiomatic
variants could replace, so that API consumers write less unsafe code; and unsafe code
inside the workset that a safe construct, or an [`ffibox`](../../tools/ffibox/SKILL.md)
primitive, could replace.

### 3.2 Contracts (`contracts`)

Safety contracts that are incorrect, incomplete or ambiguous:

- the `# Safety` obligation of a public entry point that must legitimately stay unsafe: a
  caller who honours it can still reach undefined behaviour, or it asks for something the
  implementation does not need;
- the `// SAFETY:` justification of an `unsafe` block: the invariant it claims does not
  hold on every path that reaches the block, or no comment justifies the block at all;
- an obligation stated on code that C calls once a value is handed to it, such as the
  members of a callback table a safe constructor builds for C to install: C, not the Rust
  caller, then chooses the arguments, often from data it reads, so no caller can honour it.
  What the obligation excludes is refused in Rust, in front of the C, instead, where Rust
  can test it, such as a value, a range, a null or a length. One Rust cannot test, such as
  a pointer's liveness or family, or a string's terminator, is kept by whoever hands the
  value to C: the C declaration's own contract, which the code it calls trusts as an
  export does, or an `unsafe` installer whose Rust caller vouches for it. Only an
  obligation neither covers, and Rust can test, is a finding.

A contract is tested by trying to break it: an input, a call sequence or an interleaving
that honours the obligation, or reaches the block through safe code, and still violates
what the `unsafe` relies on. Contracts are judged by the side of the boundary they serve:
the gateways through which C reaches the crate, its `ffi_export` regions, and every other
unsafe code, which sits in its `ffi_import` regions as the
[conventions](../../rust/conventions/SKILL.md) lay them out, whose items are sound for
every input their module can give them.

### 3.3 UB (`ub`)

UB in the workset's API that its UB tests missed, by where it is reached from: the safe
public API, the unsafe public API within its `# Safety` obligations, or C through an
export within the C declaration's contract. The unsafe surface includes only the API the
workset adds; a workset that made no API item unsafe has none.

### 3.4 Equivalence (`equiv`)

Functional equivalence defects in the workset's API that its equivalence tests missed,
while the C it translates exists. A divergence is a defect only when it is unintended: a
doc comment, a `CHANGELOG` entry, a named test asserting the new behaviour or a commit
message explaining it marks it deliberate, and one that corrects a C defect on purpose is
no finding.

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
traits its types lack. An item's safe API is fixed by its first merge, so its ergonomics
are reviewed there.

### 3.7 Idiom (`idiom`)

Ported implementation that transliterates its C rather than using Rust's own means: index
loops where iterators fit, status codes where `Result` and `?` fit, lengths and releases
carried by hand where ownership carries them.

### 3.8 Conventions (`conventions`)

Deviations from the [conventions](../../rust/conventions/SKILL.md), unsafe code outside its
regions included.

### 3.9 Performance (`perf`)

A component slower than the C it replaces on a representative workload, measured as the
port measures performance, with the cause where the reviewer can find it.

### 3.10 Test adequacy (`test-adequacy`)

Gaps in the workset's tests: the C and Rust execution paths, and the states and
transitions, that the codebase's external and inline test suites leave unreached, found by
reading those suites against the code and measured as
[`testing-builds`](../testing/builds/SKILL.md)'s Coverage section describes; assertions too
weak to fail when the code is wrong; tests outside the suite of their kind; and the C test
cases none carries over.

### 3.11 Revisit (`revisit`)

The findings earlier rounds filed, each rerun through its reproducer on the current tree.
One that still reproduces stays a finding of its objective; one that no longer does is
marked fixed in the new round's report, with the commit that changed the verdict; one
that was never a defect is marked so, with the reason. Each finding's class is checked
again with it.

### 3.12 Misc (`misc`)

Any other defect in the workset.

## 4. Fixes

The component's author fixes every finding; a reviewer changes nothing outside the
reviews dir. Each objective's fix:

- `unsafety`: the entry point is made safe, or the unsafe code replaced;
- `contracts`: the `# Safety` obligation or `// SAFETY:` justification is corrected, or,
  when the contract can be broken, the code it guards, and the reproducer becomes a UB
  regression test;
- `ub`, `equiv` and `logic`: the defect is patched, and the reproducer becomes a
  regression test of the same kind, a UB test, an equivalence test or a unit test, on the
  side of the component it reaches. A UB regression test either runs without triggering a
  sanitizer, or fails to compile because the patch removed the safe path that reached the
  defect;
- `ergonomics`: the API is improved, and its consumers in the crate follow;
- `idiom`, `conventions`, `perf` and `misc`: the transliteration, deviation, slowdown or
  defect is fixed;
- `test-adequacy`: the gaps are filled with tests, and the coverage measurement shows the
  delta; and
- `revisit`: every finding that still reproduces is patched, as for its objective.

Fixes follow the [conventions](../../rust/conventions/SKILL.md). Every test a fix adds is
classified as [`testing`](../testing/SKILL.md) describes and placed where the conventions
place tests of its kind.

## 5. Gates

A round's reviewer runs the component's gates, as
[`testing-gates`](../testing/gates/SKILL.md)'s Regressions section gives a merge's, on the
reviewed tree before any fix. Each true positive a gate finds is a finding of the round,
whether or not the workset holds the code it reaches: a report it leaves to no one is
lost. The author runs them again on the fixed tree before the merge.
