<!-- SKILL -->

Classify every test you add as this how-to describes, place it where the conventions'
Testing section places tests of its kind, and run it under the instruments this how-to
names. If `fix` is
enabled, a reproducer you turn into a regression test keeps its kind: a UB reproducer
becomes a UB test, an equivalence reproducer an equivalence test, and an internal defect's
regression a unit test. If `fix` is not enabled, turn no reproducer into a regression
test.

## Gates

BSan follows the sub-campaign, not the wave. Your wave is the sub-campaign's last when its
index is the highest of your subsystem's waves in
`crustify/campaigns/<campaign-id>/schedule.json`; your working branch's name gives the link
unit, subsystem and wave. In the last wave you own the sub-campaign's BSan gate. It covers
everything the sub-campaign landed, so a report on an earlier wave's items is yours to
triage as well. In every other wave, run BSan only on the individual reproducers you emit.

You also own the workspace-wide Miri gate, in every wave. Treat each Miri report of
undefined behaviour as a UB candidate of the item it touches, and give a test that Miri
stops at the foreign boundary the attribute this how-to prescribes when it lacks one.

## Regressions

Run:

```bash
cargo check --workspace
cargo clippy --workspace
cargo test --workspace
```

Every FFI, UB, and equivalence test must use the matching reusable sanitized C library or
a private sanitized replacement.

Validate under every prepared instrument. BSan is the exception, and runs with discipline:

- In the sub-campaign's last wave, run the BSan gate: the whole workspace, one invocation
  per test binary in parallel, each under a `timeout`, on the wave tip before any change.
  Start each run in the background and wait for it to exit; do not poll or read its output
  while it runs. Pursue only true positives.
- In any other wave, run BSan only on the individual reproducers you emit, each alone;
  never a test binary, a suite or the workspace.
- Only a true positive, a report that reproduces through the Rust side as a single test or
  standalone reproducer, becomes a UB finding.

Run the Miri gate over the whole workspace: one `cargo +nightly miri test` per test binary
(`--lib`, and `--test <name>` for each integration binary), in parallel, each with
`-- --skip compile_fail`, on the wave tip before any change. Start each run in the
background and wait for it to exit. The gate passes only with no Miri error: a test that
stops at the foreign boundary without the attribute gets it, and any other Miri error is a
UB candidate.

If `fix` is enabled, rerun both gates on the tree you land, after your last rebase. If
`fix` is not enabled, file each true positive either gate finds as a UB report.

If C changed, run the configured C build and baseline with the Rust feature off. For
`port`, repeat with the feature on.
