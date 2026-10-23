# ffibox

- Skill name: ffibox
- Description: Use when writing or reviewing Rust that holds memory a C
  library allocates, frees, copies, refcounts or locks — wrapping a `*-sys`
  crate's types in a safe API, or porting C code that manages such objects —
  so C's ownership and lifetime conventions are expressed through ffibox
  rather than raw pointers and hand-written `Drop` impls. Read the
  referenced documentation before writing the first wrapper: it walks from a
  C declaration to the wrapper it needs.

The document to read is ffibox's `README.md`, named by each role's `SkillSpec`.
