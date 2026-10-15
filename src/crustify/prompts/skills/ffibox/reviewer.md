<!-- SKILL -->

Review your workset's use of ffibox's primitives against the skill, and its hand-written
representations (`/// Handwritten`) against the contract ffibox would have enforced.

If you discover any soundness or ergonomics gap in ffibox itself, in its safe primitives
or its unsafe FFI seams, emit a reproducer and file a report in
`crustify/reviews/<artifact-dir>/ffibox/<defect-slug>` to demonstrate the flaw, like you
would for a defect in the target repo.

If `fix` is enabled, then emit a patch in a separate branch and worktree of the local ffibox
checkout. If `fix` is not enabled, do not.

## Tests

Do not add UB tests on the public seam interface ffibox exports on a type: it is only meant
to be exercised internally by the crate, as an escape hatch for external consumers. Test
it, for UB or functionality, with unit tests.
