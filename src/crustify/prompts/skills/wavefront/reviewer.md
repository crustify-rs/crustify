<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Artifact dirs

File each finding on a flaw in wavefront's findings in its own `<slug>` directory, holding
its report, under one of the following dirs:

- `ownership-dir`: `crustify/reviews/<artifact-dir>/wavefront/ownership/`, for flaws in the
  pointer-related findings: a wrong inference of ownership, access, nullability,
  cardinality or keepalive;
- `lifecycle-dir`: `crustify/reviews/<artifact-dir>/wavefront/lifecycle/`, for incomplete
  lifecycles: a releaser, disposer, cloner or constructor the submitted lifecycle findings
  missed.

A defect in wavefront itself is not a finding on its findings: it goes on its own branch
and worktree of the local wavefront checkout, as your prompt describes for any tool.

### Ownership

Verify Wavefront's pointer-related findings submitted by an earlier run for your workset:
ownership, access, nullability, cardinality and keepalive. File a report for each wrong
inference in `ownership-dir`, including evidence that proves the previous finding was
wrong.

If `fix` is enabled, resubmit each corrected set of findings through the CLI's `--update`.
If `fix` is not enabled, do not.

<!-- OBJECTIVE lifecycle -->
### Lifecycle

For a workset that contains `type` or `raw-lifetime` items, verify that the lifecycles
submitted to Wavefront are complete: that the earlier runs missed no releaser, disposer,
cloner or constructor. Leverage Wavefront's `--schema` CLI flag for hints on identifying
lifecycle primitives and compare them with the findings submitted earlier.

File a report for each incomplete lifecycle in `lifecycle-dir`.

If `fix` is enabled, resubmit the completed lifecycle findings through the CLI's
`--update`, and add the lifecycle representations the Rust is missing for them. If `fix`
is not enabled, do not.
<!-- /OBJECTIVE -->

<!-- OBJECTIVE unsafety -->
### Unsafety

Wavefront's plan cuts the cycles between subsystems and types. A raw pointer that stands in
for a dependency that a later scheduled batch wraps is such a cut, not a finding: leave it
out of your unsafety review.
<!-- /OBJECTIVE -->
