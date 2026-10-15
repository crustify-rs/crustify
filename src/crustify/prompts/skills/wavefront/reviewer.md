<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Artifact dirs

File each finding on a flaw in wavefront's findings in its own `<slug>` directory, holding
its report, under one of the following dirs:

- `ownership-dir`: `<reviews-dir>/wavefront/ownership/`, for flaws in the
  pointer-related findings: a wrong inference of ownership, access, nullability,
  cardinality or keepalive;
- `lifecycle-dir`: `<reviews-dir>/wavefront/lifecycle/`, for incomplete
  lifecycles: a releaser, disposer, cloner or constructor the submitted lifecycle findings
  missed.

A defect in wavefront itself is not a finding on its findings: it goes on its own branch
and worktree of the local wavefront checkout, as your prompt describes for any tool.

## Analysis

The following augment your Analysis step.

### Ownership

Verify Wavefront's pointer-related findings submitted by an earlier run for your workset:
ownership, access, nullability, cardinality and keepalive. A wrong inference is a finding.

### Lifecycle (`lifecycle`)

For a workset that contains `type` or `raw-lifetime` items, verify that the lifecycles
submitted to Wavefront are complete: that the earlier runs missed no releaser, disposer,
cloner or constructor. Leverage Wavefront's `--schema` CLI flag for hints on identifying
lifecycle primitives and compare them with the findings submitted earlier. An incomplete
lifecycle is a finding.

### Cycle cuts

When `unsafety` is among your objectives: Wavefront's plan cuts the cycles between
subsystems and types. A raw pointer that stands in for a dependency that a later scheduled
batch wraps is such a cut, not a finding: leave it out of your unsafety review.

## Evidence

File each wrong inference in `ownership-dir` and each incomplete lifecycle in
`lifecycle-dir`, with a report including the evidence that proves the submitted finding
wrong or incomplete.

## Fixes

If `fix` is enabled, resubmit each corrected or completed set of findings through the CLI's
`--update`, and add the lifecycle representations the Rust is missing for a completed
lifecycle. If `fix` is not enabled, do not.
