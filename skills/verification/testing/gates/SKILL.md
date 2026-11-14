---
name: testing-gates
description: "The regression gates work lands through, by event: a batch's scoped gates, a wave's, a module's end or switch from C and a ship point's; campaign mode and packaging, sanitizers, BSan and Miri, rebases under the landing lock, and a port batch's export checks. Read before running a batch's gates, landing, integrating a module or shipping."
---

# Testing gates

The gates every landing passes, over the tests [`testing`](../SKILL.md) classifies and the
builds [`testing-builds`](../builds/SKILL.md) describes.

## 1. Regressions

Every batch checks, formats and lints the workspace on the tree it lands, with warnings
denied, as [`toolchain`](../../../rust/toolchain/SKILL.md) describes, and tests what its
change can affect: its module and the modules that depend on it, as `modules.json` records
them, each by its tests' module paths.

Every build of those gates runs in the raw bindings' campaign mode, as
[`bindgen`](../../../rust/bindgen/SKILL.md)'s Build modes section describes, so that each fails when the
committed bindings do not match their input. A batch that changed the raw bindings, or a
landing that changes `c/`, also packages the safe crate, built alone in bundled mode from
the C it packages, with no build variant selected. Until the out-of-tree wrappers are
published, each crate the package depends on is patched to its local source, so that the
package builds alone.

The tests run against the matching variant, or a private replacement, and each event runs
them to its own depth:

- a batch: the tests above, plain and under ASan/UBSan, and its own tests under each other
  sanitizer its items call for, such as TSan where it asserts `Send` or `Sync` or adds a
  threaded callback, or MSan where C leaves memory it hands over partly unwritten;
- a wave's end, and a module's end, its switch in a port: the workspace's tests, plain,
  under every available sanitizer, under Miri and under BSan as below, less each stage's
  slow list;
- a full run: every test of the workspace under every stage, the slow lists not applied.
  It runs in the background, beside the campaign's work, by default after every fifth
  module the campaign integrates; and
- a ship point: a full run, with the coverage measurement.
<!-- TODO: a wave's end and a module's end are run by the wave's last review batch and the
module pass, so a campaign without review runs neither: they need an owner there. -->

The slow list is the campaign's skip file, which holds, per stage, the tests that take over a
minute under that stage, each by its exact name with the time measured. A test on it is
skipped at a wave's and a module's end and runs in every full run, so that the ends stay
short enough to run each time and no test goes unrun for long. A test joins the list when
an end's run measures it over the minute, and leaves when a full run measures it under. A
skip weakens a gate: the list's changes since the last ship point are put to the user at
each ship point.

BSan, when available, is run for every batch, at a wave's end and at a module's end:

- For a batch, it runs only on the individual tests or reproducers the batch expects to
  trigger it, each by exact name and alone; never on a whole test binary, a suite or the
  workspace.
- At a wave's and a module's end, it runs as a gate over the whole workspace, less its
  slow list, one invocation per test binary, as many side by side as
  [`concurrency`](../../../operations/concurrency/SKILL.md) describes, each under a `timeout`.

A batch runs the tests it wrote under Miri. Miri is also run at every wave's and module's
end, as a gate over the whole workspace, less its slow list: one Miri run on the pinned
nightly per test binary, the library's and each integration suite's, as many side by side as
[`concurrency`](../../../operations/concurrency/SKILL.md) describes, each skipping the
compile-fail tests. The gate passes only
with no Miri error: a test that stops at the foreign boundary without the attribute gets
it, and any other Miri error is a UB candidate of the item it touches.

`end-gates`, beside this skill and documented by its `--help`, runs a wave's and a
module's end gates so, over a snapshot of the tree, so that work goes on in the tree while
they run: the format check and the lints with warnings denied, once per export-feature set
the batch checks, the workspace under each variant, Miri and BSan per test binary, and the
slow list's tests skipped by name, each skip checked against its binary's test list before
anything runs. A batch's own format and lint gates run the same way, over the commit it
lands, so that the result it records is that tree's.

Each gate run starts in the background and is waited on to exit; its output is neither
polled nor read while it runs. BSan reports false positives at the foreign boundary, so
only a true positive, a report that reproduces through the Rust side as a single test or
standalone reproducer, becomes a UB finding.

Every translation and review batch measures the consumer-facing API of its items against
the tip it rebased onto, each change classified as the dashboard's API stability columns
name them. An item's API is fixed by its first landing: a later landing
that changes or removes it, a port, a later stage, a rebind or a review fix alike, breaks
its consumers, and is kept only with its reason recorded in the batch's notes, such as a
soundness fix; the measure does not fail the gate. A module's integration measures every
item of the module against the module's base, and a ship point the whole crate against the
previous ship point.

When C changed, the configured C build and baseline run. A wrap-only batch with no C
change does not need the full C baseline.

A batch validates its own change on its own base first. Its rebase onto the integration
branch, under the landing lock that [`versioning`](../../../operations/versioning/SKILL.md)'s Landing section
describes, then combines that change with the work landed since: the gates run again are
those that could catch a regression the combination introduces, judged from what the
batch's change and the rebased-in changes touch and how they could interact. A gate that
neither side's changes could affect keeps the result it had, and a rebase that conflicts
makes the resolved tree new work of the batch's own.

A `port` batch changes no C: its gates are those above, run against the variants with its
module's export feature off, so that the ported Rust is tested beside the C it replaces.
It also checks and lints the safe crate with that feature on, which compiles the module's
gateway without linking it, and each export is checked at compile time against the raw
binding of the C declaration it replaces, so that a signature that drifts from C's fails
to build.

A module's switch removes its translation unit, and the C tests tied to it that reach
its internals, from `c/`, rebuilds the variants from the C that remains and deletes the
module's export feature, as
[`porting-workflow`](../../../workflows/porting-workflow/SKILL.md)'s Builds section
describes. Its gates are a module's end's, in campaign mode over the rebuilt variants, and
the target's remaining C tests, which link the remaining C and the safe crate's Rust static
library, so that the C reaches the ported module through its exports: the module's tied C
tests that use only its public API among them, as the porting workflow's Tests follow
their modules section describes. Before a tied C test leaves, the cases none of the
module's `unit_pub` tests carries over are listed, as [`testing`](../SKILL.md)'s C tests
carried over section describes.
