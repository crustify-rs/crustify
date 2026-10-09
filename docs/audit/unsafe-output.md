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

- the dated nightly pinned in `src/crustify_audit/unsafe_driver/rust-toolchain.toml`
  (a `rustc_private` driver builds only against the compiler internals it was
  written for), with `rustc-dev` and `llvm-tools`;
- successful `cargo metadata`;
- a workspace that builds under the nightly driver, including its native
  dependencies.

When measurement cannot run, `counts` is `null` and `counts_unavailable`
contains the failure. The tool does not substitute approximate results.

Generated `-sys` binding crates are excluded from the aggregate because they
are not the wrapper being audited.

## Document shape

- `crate_path`: audited Cargo workspace.
- `counts`: aggregate compiled-code metrics (numbers only), or `null`.
- `counts_unavailable`: failure text when counts are unavailable.
- `derived`: ratios and sums calculated from counts.
- `undocumented_unsafe`: a lexical count of `unsafe` sites with no `// SAFETY:`
  comment shortly above them (`sites`, `documented`, `undocumented`,
  `per_file`). It needs no build and approximates
  `clippy::undocumented_unsafe_blocks`: a long comment above its lookback
  window, or a site inside a macro, can disagree with the lint.
- `sites`: present when `--sites` names counters; see Counter sites.

Unsafe-block totals provide context only. A C wrapper must contain unsafe code,
and combining many small unsafe blocks into fewer large ones improves the count
without improving the code.

## Seam, smell and visibility

The seam is where a wrapper is expected to be unsafe. A function is seam when
its name is a conversion or lifecycle hook (`as_ptr`, `as_c_ptr`, `from_ptr`,
`from_void_ptr`, `from_raw*`, `into_raw*`, `to_raw`, and the unsafe trait
methods `c_drop`, `c_drop_len`, `c_dup`, `c_clone_len`, `c_up_ref`,
`c_is_sole_owner`, `c_lock`, `c_unlock`, `c_dispose`; the full list is
`SEAM_FNS` in the driver), or when it has a C ABI or `#[no_mangle]`. A
raw-pointer position is also seam when it points to the method's own `Self`.
Everything else is smell, split by the declaring function's visibility:
"pub" is rustc's effective visibility, callable from outside the crate. A
trait-impl method reachable through a public trait and type is pub; a `pub`
item in a private module is not, unless it is re-exported.

Three counter families partition this way:

- `unsafe_fns` = `unsafe_fns_seam` + `unsafe_fns_pub_smell` +
  `unsafe_fns_priv_smell`.
- `raw_ptr_args` + `raw_ptr_rets` + `raw_ptr_fields` = `raw_ptr_seam` +
  `raw_ptr_pub_smell` + `raw_ptr_priv_smell`. `raw_ptr_args` and
  `raw_ptr_rets` are the positions in function signatures, `raw_ptr_fields`
  those in the fields of structs and unions the crate declares. A field is seam
  when its struct is a handle (storing the pointer is what a handle is for);
  otherwise it is pub smell when it is reachable from outside the crate (a
  `pub` field of an exported type), else private smell. Generated bindings
  compiled into the crate are skipped: files under the build script's
  `OUT_DIR` and files named `bindings.rs`; bindings in a `-sys` crate are
  excluded with that crate. `raw_ptr_wrapped` counts the smell positions whose
  pointee is a C type that already has a wrapper.
- `void_ptr_seam` + `void_ptr_pub_smell` + `void_ptr_priv_smell` are the
  `*const c_void` / `*mut c_void` positions, a subset of the raw-pointer ones.

A position is every raw pointer in a parameter, return or field type, including
those nested in references, generic arguments (`Option<*const T>`), tuples,
arrays and slices. A pointer to a pointer (`*mut *mut T`) is one position,
fn-pointer types are not entered, and `PhantomData<*const T>` is a zero-sized
marker, not a position. Type aliases are resolved, so
`type P = *const T` counts as a raw pointer.

The derived fields:

- `unsafe_fn_smell`: `unsafe_fns_pub_smell + unsafe_fns_priv_smell`.
- `raw_ptr_smell`: `raw_ptr_pub_smell + raw_ptr_priv_smell`.
- `unsafe_fn_pub_ratio`: `unsafe_fns_pub_smell / unsafe_fns`.
- `raw_ptr_seam_ratio`: fraction of raw-pointer positions at the seam.
- `unsafe_loc_ratio` and `loc_per_unsafe_block`: context, not a score.

## Wrappers and references into C memory

A wrapper is found by its shape alone: a struct that is either a handle, a
`#[repr(transparent)]` newtype whose one non-zero-sized field is a raw pointer,
`NonNull` or reference, or a layout newtype, `#[repr(transparent)]` or
`#[repr(C)]`, that embeds by value a `#[repr(C)]` type from another crate
(the C type from the `-sys` crate). Same-crate `#[repr(C)]` fields are searched
through, so C's own nested structs are not mistaken for wrappers.
`wrapper_newtypes` counts the layout newtypes; `wrapper_newtypes_declared`,
`_undeclared` and `wrapper_declared_nonconformant` compare that set with the
types that declare `CCell`.

A layout newtype's memory is C's when it is reached through a C pointer, so a
Rust reference to it asserts `noalias`, `readonly` or validity over memory C
may write. Access goes through the handles instead.

- `ref_to_type_wrapper_sanctioned` and `ref_to_type_wrapper_smell` partition
  the `&W` / `&mut W` positions in function signatures (the receiver included).
  Sanctioned are the accessors `as_ref` / `as_mut`, which hand out borrowed
  handles over a Rust-owned value, and methods of impls of the standard value
  traits `Clone`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash` and `Debug`,
  derived or not. The smell should be 0.
- `ref_to_type_wrapper_body_smell` counts the same hazard inside function
  bodies: an expression that forms a reference to a layout wrapper from a raw
  pointer -- `&*p`, `&mut *p`, `&(*p).f` (casts included), an autoref through
  `*p` for a `&self` method, or a call to a function from another crate that
  takes a raw pointer or `NonNull` and returns a type holding `&W`
  (`p.as_ref()`, `NonNull::as_ref`, `slice::from_raw_parts`). Calls to the
  crate's own functions are not counted at the call site; their bodies are.
  A `PhantomData<&W>` marker holds no reference and is not counted. Nothing is
  sanctioned: target 0.
- `field_proj_wrapped` counts field accesses `(*p).field` through a raw pointer
  to a wrapped C type or a wrapper, and `field_proj_outside_impl` the subset
  outside any `impl` or trait body. `field_ref_wrapped` counts the references
  `&(*p).field` / `&mut (*p).field` among them; raw borrows (`&raw const`,
  `addr_of!`) are not counted.

- `deref_impl_on_wrapper` counts impls of `core::ops::Deref` or `DerefMut`
  whose `Self` is a wrapper, layout newtype or handle. Such an impl turns every
  `*w` and auto-deref into a reference to its target, typically the C object,
  outside the handles. Nothing is sanctioned: target 0.

Read these together with `wrapper_newtypes`; when there are no wrapper
newtypes, zero is vacuous. The driver cannot tell a pointer to C memory from
one to a Rust-owned value, so a site means "check where this pointer comes
from".

## Counter sites

`--sites COUNTER [COUNTER ...]` (or `--sites all`) adds a `sites` record beside
`counts`, with one list per named counter: where that counter's increments are
in the source, as `[{"file": .., "count": N, "lines": [..]}]` per file. `count`
is the number of increments in that file, so a counter's per-file counts sum to
its value in `counts`; `lines` are the distinct lines they fell on, sorted. A
signature position (raw/void pointer, `unsafe fn`, `ref_to_type_wrapper_*`) is
sited at its function's signature line; a block, dereference, projection,
reference or call at the expression. A site inside macro output
(`define_ctype!`, `#[derive]`) is the line in the measured crate that invoked
the macro. Only counters that count source locations take `--sites`: the line
and statement totals (`code_lines`, `total_stmts`, `unsafe_block_*lines`,
`unsafe_block_stmts`) have none.

## Known limitations

- **References into C memory the counters miss.** `field_ref_wrapped` matches
  only `&(*p).field` one field deep, so `&(*p).a.b` and `&(*p).arr[i]` are not
  counted; an autoref on a field (`(*p).field.method()` with `&self`) is not
  counted; and a reference to the C type itself (`&*p` with
  `p: *const ffi::T`, or `NonNull<ffi::T>::as_ref`) is counted by no counter,
  since `ref_to_type_wrapper_*` only cover wrapper types. See `docs/TODO.md`.
- **Signatures and fields only for pointer positions.** Raw-pointer, `c_void`
  and `ref_to_type_wrapper_*` signature counters read the parameter and return
  types of functions with bodies; raw-pointer and `c_void` positions also
  include struct and union fields. Raw pointers in locals, casts, closure parameters, enum variants and
  statics are not positions, `NonNull` is never one, and a trait method
  declared without a default body is not counted.
- **Seam by name.** A function is seam because of its name or ABI, not because
  of what it does: a hand-written `as_ptr` is sanctioned like a generated one.
- **Pointer origin.** No counter can tell C-owned memory from Rust-owned memory
  behind a pointer.
