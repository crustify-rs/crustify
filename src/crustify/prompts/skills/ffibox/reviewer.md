<!-- SKILL -->

Review your workset's use of ffibox's primitives against the skill, and its hand-written
representations (`/// Handwritten`) against the contract ffibox would have enforced.

A soundness or ergonomics gap in ffibox itself, in its safe primitives or its unsafe FFI
seams, is a defect in a tool: it goes on its own branch and worktree of the local ffibox
checkout, as your prompt describes.

## Tests

Do not add UB tests on the public seam interface ffibox exports on a type: it is only meant
to be exercised internally by the crate, as an escape hatch for external consumers. Test
it, for UB or functionality, with unit tests.
