# Deterministic `unsafe` output

`crustify scan-unsafe WORKDIR` builds the workspace through a rustc driver over
HIR and type checking. Its output is a deterministic description of the code
that the build's active `cfg` selects—not a soundness verdict or quality score.

The scan writes no file. `--json` prints the document on stdout and the caller
redirects it wherever that run's record belongs — for a campaign, the wave or
batch artifact directory. Where a scan is kept is the caller's decision, so
nothing here creates paths or edits a `.gitignore`.

## Availability

The scan requires:

- nightly Rust with `rustc-dev` and `llvm-tools`;
- successful `cargo metadata`;
- a workspace that builds under the nightly driver, including its native
  dependencies.

When measurement cannot run, `counts` is `null` and `counts_unavailable`
contains the failure. The tool does not substitute approximate results.

Generated `-sys` binding crates are excluded from the aggregate because they
are not the wrapper being audited.

## Document shape

- `crate_path`: audited Cargo workspace.
- `counts`: aggregate compiled-code metrics, or `null`.
- `counts_unavailable`: failure text when counts are unavailable.
- `derived`: ratios and boundary-oriented comparisons calculated from counts.
- `seed` and `entries`: present when `--name` requests named source sites.
- `sites`: present when `--sites` names counters; see Counter sites.

Unsafe-block totals provide context only. A C wrapper must contain unsafe code,
and combining many small unsafe blocks into fewer large ones improves the count
without improving the code.

The more categorical derived fields describe obligations outside the expected
FFI seam:

- `unsafe_fn_smell`: unsafe functions not classified as seam functions,
  `counts.unsafe_fns_pub_smell + counts.unsafe_fns_priv_smell`. With
  `counts.unsafe_fns_seam` they partition `counts.unsafe_fns`.
- `raw_ptr_smell`: raw-pointer argument/return positions not classified as
  seam positions, `counts.raw_ptr_pub_smell + counts.raw_ptr_priv_smell`. With
  `counts.raw_ptr_seam` they partition `raw_ptr_args + raw_ptr_rets`.
  `counts.raw_ptr_wrapped` counts the smell positions whose pointee is a C
  type that already has a wrapper.
- `void_ptr_seam`, `void_ptr_pub_smell`, `void_ptr_priv_smell` (counts): the
  `*const c_void` / `*mut c_void` positions among the raw-pointer positions,
  partitioned the same way.

"Pub" is rustc's effective visibility: callable from outside the crate. A
trait-impl method reachable through a public trait and type is pub; a `pub`
item in a private module is not. A position is every raw pointer in a parameter or
return type, including those nested in references, generic arguments
(`Option<*const T>`), tuples, arrays and slices. A pointer to a pointer
(`*mut *mut T`) is one position, and fn-pointer types are not entered. Type
aliases are resolved, so `type P = *const T` counts as a raw pointer.
- `unsafe_fn_pub_ratio`: fraction of unsafe functions that are public smell
  (`unsafe_fns_pub_smell / unsafe_fns`).
- `raw_ptr_seam_ratio`: fraction of raw-pointer positions at the seam.

`ref_to_type_wrapper_sanctioned` and `ref_to_type_wrapper_smell` partition the
`&W` / `&mut W` positions in function signatures (the receiver included) where
`W` is a layout-compatible wrapper type, whose memory C may mutate when it is
reached through a C pointer. Sanctioned are the accessors `as_ref` / `as_mut`
that hand out borrowed handles over a Rust-owned value, and methods of impls of
the standard value traits `Clone`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`,
`Hash` and `Debug`, derived or not. The smell should be 0. Read both together
with `wrapper_newtypes`; when there are no wrapper newtypes, zero is vacuous.

## Counter sites

`--sites COUNTER [COUNTER ...]` (or `--sites all`) adds a `sites` record beside
`counts`, with one list per named counter: where that counter's increments are
in the source, as `[{"file": .., "count": N, "lines": [..]}]` per file, lines
sorted and deduplicated, so `count` is the number of distinct lines. A
signature position (raw/void pointer, `unsafe fn`, `ref_to_type_wrapper_*`) is
sited at its function's signature line; a block, dereference, projection or
call at the expression. Only counters that count source locations take
`--sites`: the line and statement totals (`code_lines`, `total_stmts`,
`unsafe_block_*lines`, `unsafe_block_stmts`) have none.

## Named sites

Repeat `--name` to search for C type or symbol names:

```sh
crustify scan-unsafe WORKDIR --name SSL SSL_new --name SSL_free
```

Names resolve independently within each compiled workspace crate, and each
entry retains its `crate` field.

For types, entries may contain:

- `raw_ptr_sites`: raw-pointer declarations in arguments, returns, fields, and
  explicitly typed locals.
- `raw_deref_sites`: dereference expressions for matching pointers.
- `deref_impl_sites` and `deref_mut_impl_sites`: manual wrapper dereference
  implementations.
- `slice_ref_sites` and `slice_mut_sites`: wrapper slice types and expressions
  that materialize them, including inferred `slice::from_raw_parts` calls.

For symbols, matching uses the Rust item name or linked/exported C name.
Signature/body pointer declarations and body dereferences are attributed to the
symbol; calls to external C functions attribute the enclosing wrapper
function's corresponding sites. Wrapper-specific dereference and slice fields
remain type-only.
