<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

### Analysis findings

Verify Wavefront's analysis findings submitted by an earlier run for your workset:
ownership, access, nullability, cardinality and keepalive. File a report describing each
defect in `wavefront-dir`, including evidence that proves the previous finding was wrong or
incomplete.

If `fix` is enabled, resubmit each corrected set of findings through the CLI's `--update`.
If `fix` is not enabled, do not.

<!-- OBJECTIVE lifecycle -->
### Lifecycle

For a workset that contains `type` or `raw-lifetime` items, verify that their lifecycle
primitives are complete: that the earlier runs missed no releaser, disposer, cloner or
constructor, and that every ownership variant the analysis found has a representation.
Leverage Wavefront's `--schema` CLI flag for hints on identifying lifecycle primitives and
compare them with the findings submitted earlier.

File a report for each gap in `lifecycle-dir`.

If `fix` is enabled, add each missing lifecycle representation, and resubmit the corrected
lifecycle findings through the CLI's `--update`. If `fix` is not enabled, do not.
<!-- /OBJECTIVE -->

<!-- OBJECTIVE unsafety -->
### Unsafety

Wavefront's plan cuts the cycles between subsystems and types. A raw pointer that stands in
for a dependency that a later scheduled batch wraps is such a cut, not a finding: leave it
out of your unsafety review.
<!-- /OBJECTIVE -->
