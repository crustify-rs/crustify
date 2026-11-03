# wavefront › verification/reviewing

## Objectives

### Lifecycle (`lifecycle`)

Lifecycles submitted to wavefront that are incomplete: a releaser, disposer, cloner or
constructor that the findings of the batches that bound or ported `type` items, or items
of the foundational modules, missed. They are checked against the lifecycle primitives
`docs/type-lifecycle.md` identifies.

### The submitted findings

Whatever the objectives, a review checks the pointer-related findings an earlier run submitted for the
workset: ownership, access, nullability, cardinality and keepalive. A wrong inference is a
finding.

### Unsafety

The plan cuts the cycles between modules and types. A raw pointer that stands in for a
dependency a later scheduled batch wraps is such a cut, not an `unsafety` finding.

## Reports

A finding on wavefront's findings is filed in its own `<slug>` directory, with its report
and the evidence that proves the submitted finding wrong or incomplete, under:

- `<reviews dir>/wavefront/ownership/`, for a wrong pointer-related inference; or
- `<reviews dir>/wavefront/lifecycle/`, for an incomplete lifecycle.

A defect in wavefront itself is no finding on its findings: it is filed on a dedicated
branch and worktree of the local wavefront checkout, as any tool defect is.

## Fixes

Under `fix`, each corrected or completed set of findings is submitted again through the
CLI's `--update`, and a completed lifecycle gets the representations the Rust is missing.

## Plan corrections

A correction of wavefront's planning artifacts is filed in the reviews sub-directory of
what it amends:

- `crustify/reviews/planner/modules/` for a configuration, with the `modules.json`
  finding it follows from;
- `crustify/reviews/planner/chased-casts/` for `chased_casts.csv`: for each `add` row the
  chain followed, hop by hop with `file:line`, or the hop that breaks it; for each `drop`
  row the cast sites that derive the edge, and why they are no type relation; and
- `crustify/reviews/planner/type-generators/` for `type_generators.csv`: the macro's
  invocation sites, conditional ones included, and the shapes they mint.

A report on a T3 table also states the DAG change the edit makes.
