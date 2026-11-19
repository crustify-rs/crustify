---
name: testing-gates
description: "The regression gates a port passes, by event: a component's own gates, a merge into the working branch, a periodic full run, a component's C leaving the build, and the final run; the slow list, sanitizers, BSan and Miri, merges onto newer work, and the export checks. Read before running gates, merging a component or removing a component's C from the build."
---

# Testing gates

The gates the port passes, over the tests [`testing`](../SKILL.md) classifies and the
builds [`testing-builds`](../builds/SKILL.md) describes. The gate results a run records
in `crustify/STATUS.md` are the latest of each component's: its test counts and the
instruments it passed under. A gate that fails leaves its component's row saying so.

## 1. Regressions

Every component's work checks, formats and lints the workspace on the tree it merges,
with warnings denied, as [`toolchain`](../../../rust/toolchain/SKILL.md) describes, and
tests what its change can affect: the component and the components that depend on it,
each by its tests' module paths.

Every build of those gates links the C as the agent's recorded builds give it, as
[`bindgen`](../../../rust/bindgen/SKILL.md)'s Building section describes, so that each
fails when the committed bindings do not match their input. A change to the raw bindings,
or to the C, also builds the crate alone, as a dependent would, from the C it packages.

The tests run against the matching build, or a private replacement, and each event runs
them to its own depth:

- a component's own work: the tests above, plain and under ASan/UBSan, and its own tests
  under each other sanitizer its items call for, such as TSan where it asserts `Send` or
  `Sync` or adds a threaded callback, or MSan where C leaves memory it hands over partly
  unwritten;
- a merge into the working branch, and a component's C leaving the build: the
  workspace's tests, plain, under every available sanitizer, under Miri and under BSan
  as below, less each instrument's slow list;
- a full run: every test of the workspace under every instrument, the slow lists not
  applied. It runs in the background, beside the port's work, at least after every few
  merged components, and its failures are handed to the authors of the components they
  reach; and
- the final run, before the report: a full run, with the coverage measurement, on the
  tree the report describes.

The slow list is the port's skip file, `crustify/slow-tests`, which holds, per
instrument, the tests that take over a minute under it, each by its exact name with the
time measured. A test on it is skipped at a merge and runs in every full run, so that
merges stay short enough to gate every time and no test goes unrun for long. A test joins
the list when a merge's run measures it over the minute, and leaves when a full run
measures it under. A skip weakens a gate: the list and its changes are named in the
report.

BSan, when available, is run for a component's own work and at each merge:

- For a component's own work, it runs only on the individual tests or reproducers the
  work expects to trigger it, each by exact name and alone; never on a whole test binary,
  a suite or the workspace.
- At a merge, it runs as a gate over the whole workspace, less its slow list, one
  invocation per test binary, several side by side, each under a `timeout`.

The slow list keeps a slow test out of the merges, not out of a full run, which a test
BSan cannot finish within that `timeout` fails every time. Such a test is sized for BSan:
in the configuration BSan's build sets, it runs fewer inputs, chosen to keep reaching
every path it checks, while every other build runs it whole.

A component's author runs the tests it wrote under Miri. Miri is also run at every merge,
as a gate over the whole workspace, less its slow list: one Miri run on the pinned nightly
per test binary, the library's and each integration suite's, several side by side, each
skipping the compile-fail tests. The gate passes only with no Miri error: a test that
stops at the foreign boundary without the attribute gets it, and any other Miri error is
a UB candidate of the item it touches.

`end-gates`, beside this skill and documented by its `--help`, runs a merge's and a full
run's gates so, over a snapshot of the tree, so that work goes on in the tree while they
run: the format check and the lints with warnings denied, the workspace under each build,
Miri and BSan per test binary, and the slow list's tests skipped by name, each skip
checked against its binary's test list before anything runs. A component's own format and
lint gates run the same way, over the commit it merges, so that the result it records is
that tree's.

Each gate run starts in the background and is waited on to exit; its output is neither
polled nor read while it runs. BSan reports false positives at the foreign boundary, so
only a true positive, a report that reproduces through the Rust side as a single test or
standalone reproducer, becomes a UB finding.

Every merge measures the consumer-facing API of its items, C and Rust, against the tip it
merges onto. An item's API is fixed by its first merge: a later merge that changes or
removes it, a review fix included, breaks its consumers, and is kept only with its reason
recorded in its commit message, such as a soundness fix; the measure does not fail the
gate. The final run measures the whole crate against the C's installed headers.

When the C changed, the C build and its tests run again.

A component's work is validated on its own base first. Merging it onto the working branch
then combines that change with the work merged since: the gates run again are those that
could catch a regression the combination introduces, judged from what the component's
change and the merged-in changes touch and how they could interact. A gate that neither
side's changes could affect keeps the result it had, and a merge that conflicts makes the
resolved tree new work of the component's own.

While a component's C is still built beside its Rust, its gates run against builds that
keep that C, so that the ported Rust is tested beside the C it replaces. Each export is
checked at compile time against the raw binding of the C declaration it replaces, so that
a signature that drifts from C's fails to build.

When a component's C leaves the build, its gates are a merge's, over builds of the C that
remains, and the target's remaining C tests, which link the remaining C and the Rust
static library, so that the C reaches the ported component through its exports: the
component's tied C tests that use only its public API among them. Before a tied C test
leaves, the cases none of the component's `unit_pub` tests carries over are listed, as
[`testing`](../SKILL.md)'s C tests carried over section describes.
