---
name: testing-gates
description: "The regression gates work lands through: check, format, lint and test, campaign mode and packaging, sanitizers, BSan and Miri, rebases under the landing lock, and a port batch's and a module integration's gates. Read before running a batch's gates, landing, or integrating a module."
---

# Testing gates

The gates every landing passes, over the tests [`testing`](../SKILL.md) classifies and the
builds [`testing-builds`](../builds/SKILL.md) describes.

## 1. Regressions

Every batch checks, formats, lints and tests the workspace on the tree it lands, with
warnings denied, as [`toolchain`](../../../rust/toolchain/SKILL.md) describes:

```bash
cargo check --workspace --all-targets
cargo +nightly-<date> fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Every build of those gates runs in the raw bindings' campaign mode, as
[`bindgen`](../../../rust/bindgen/SKILL.md)'s Build modes section describes, so that each fails when the
committed bindings do not match their input. A batch that changed the raw bindings, or a
landing that changes `c/`, also packages the safe crate, built alone in bundled mode from
the C it packages:

```bash
CRUSTIFY_BUILD_VARIANT= cargo package --config 'patch.crates-io.<crate>.path="<path>"' ...
```

Until the out-of-tree wrappers are published, each crate the package depends on is patched
to its local source, so that the package builds alone.

Every FFI, UB, and equivalence test runs against the matching reusable sanitized C library
or a private sanitized replacement, and under every available sanitizer.

BSan, when available, is run for every batch and at module end:

- For a batch, it runs only on the individual tests or reproducers the batch expects to
  trigger it, each by exact name and alone; never on a whole test binary, a suite or the
  workspace.
- At module end, it runs as a gate over everything the module landed: the
  whole workspace, one invocation per test binary, as many side by side as
  [`concurrency`](../../../operations/concurrency/SKILL.md) describes, each under a `timeout`.

A batch runs the tests it wrote under Miri. Miri is also run after every wave, as a gate
over the whole workspace: one
`cargo +nightly-<date> miri test` per test binary (`--lib`, and `--test <name>` for each
integration binary), as many side by side as [`concurrency`](../../../operations/concurrency/SKILL.md) describes,
each with `-- --skip compile_fail`. The gate passes only
with no Miri error: a test that stops at the foreign boundary without the attribute gets
it, and any other Miri error is a UB candidate of the item it touches.

Each gate run starts in the background and is waited on to exit; its output is neither
polled nor read while it runs. BSan reports false positives at the foreign boundary, so
only a true positive, a report that reproduces through the Rust side as a single test or
standalone reproducer, becomes a UB finding.

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

A module's integration removes its translation unit and the C tests tied to it from `c/`,
rebuilds the variants from the C that remains and turns the module's export feature on, as
[`porting-workflow`](../../../workflows/porting-workflow/SKILL.md)'s Builds section describes. Its gates
are those above, in campaign mode over the rebuilt variants, and the target's remaining C
tests, which link the remaining C and the safe crate's Rust static library, so that the C
reaches the ported module through its exports; the C tests tied to the module leave with
it, as the porting workflow's Tests follow their modules section describes.
