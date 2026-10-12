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
- `ffibox`: present with `--ffibox`; see ffibox surface. `null` when there are
  no counts.

Unsafe-block totals provide context only. A C wrapper must contain unsafe code,
and combining many small unsafe blocks into fewer large ones improves the count
without improving the code.

## The crate's own surface: visibility and safety

Every counter measures what the scanned crate itself defines: its types, its
fns and its methods. Items of other crates are never counted (ffibox's `CBox`,
`CArc` and their methods, std's), and neither are methods implementing another
crate's trait (`Clone`, `Drop`, ffibox's `CDrop`, ..), whose signature that
crate fixed. "pub" is rustc's effective visibility, reachable from outside the
crate: a `pub` item in a private module is not, unless it is re-exported, and a
`pub(crate)` item (such as the constructors `define_ctype!` emits) is private.

- `unsafe_fns` = `unsafe_fns_pub` + `unsafe_fns_priv`. `unsafe_fns_pub` is the
  public unsafe surface: every obligation the crate exports to its callers.
- Every raw-pointer position falls in exactly one of six counters, by where
  it sits:

  ```text
  raw_ptr_ty_pub,       raw_ptr_ty_priv          fields of types
  raw_ptr_fn_pub_safe,  raw_ptr_fn_pub_unsafe    fn signatures (args and return)
  raw_ptr_fn_priv_safe, raw_ptr_fn_priv_unsafe
  ```

  A type's fields count by the TYPE's visibility, private fields of a public
  type included, since they are its representation. A signature counts by the
  fn's visibility and its safety: `_safe` is a safe fn, reachable from safe
  code, `_unsafe` an `unsafe fn`, whose caller has taken the obligation on. The
  raw pointers on the safe public interface are `raw_ptr_ty_pub` +
  `raw_ptr_fn_pub_safe`. `raw_ptr_has_ty_wrapper` counts the positions whose pointee is a C type that already has a
  wrapper. Generated bindings compiled into the crate are skipped: files under
  the build script's `OUT_DIR` and files named `bindings.rs`; bindings in a
  `-sys` crate are excluded with that crate.
- `void_ptr_ty_{pub,priv}` and `void_ptr_fn_{pub,priv}_{safe,unsafe}` count
  the `*const c_void` / `*mut c_void` positions among them, partitioned the
  same way.

The C-ABI gateway (`#[no_mangle]` / `#[export_name]` / `extern "C"` fns) is
counted like any other fn; its unsafe blocks are also counted apart, in
`unsafe_blocks_ffi_export`.

`safe_fns_pub` and `safe_fns_priv` count the safe functions and methods with
a body, on the same terms as `unsafe_fns_*`: by visibility, leaving out
methods implementing another crate's trait. So the crate's own functions are
`fns_pub` = `safe_fns_pub` + `unsafe_fns_pub` and likewise `fns_priv`, both
given in `derived`. Trait method declarations without a body are not counted.

A position is every raw pointer in a parameter, return or field type, including
those nested in references, generic arguments (`Option<*const T>`), tuples,
arrays and slices. A pointer to a pointer (`*mut *mut T`) is one position,
fn-pointer types are not entered, and `PhantomData<*const T>` is a zero-sized
marker, not a position. Type aliases are resolved, so
`type P = *const T` counts as a raw pointer.

The derived fields:

- `fns_pub` / `fns_priv`: `safe_fns_pub + unsafe_fns_pub`, likewise `_priv`.
- `unsafe_fn_pub_ratio`: `unsafe_fns_pub / unsafe_fns`.
- `unsafe_fn_share_of_pub_fns`: `unsafe_fns_pub / fns_pub`.
- `raw_ptr_pub`: `raw_ptr_ty_pub + raw_ptr_fn_pub_safe + raw_ptr_fn_pub_unsafe`.
- `raw_ptr_pub_safe_interface`: `raw_ptr_ty_pub + raw_ptr_fn_pub_safe`.
- `unsafe_loc_ratio` and `loc_per_unsafe_block`: context, not a score.

## Wrappers and references into C memory

A wrapper is found by its shape alone: a struct that is either a handle, a
`#[repr(transparent)]` newtype whose one non-zero-sized field is a raw pointer,
`NonNull` or reference, or a layout newtype, `#[repr(transparent)]` or
`#[repr(C)]`, that embeds by value a `#[repr(C)]` type from another crate
(the C type from the `-sys` crate). Same-crate `#[repr(C)]` fields are searched
through, so C's own nested structs are not mistaken for wrappers.
`ty_wrapper_newtypes` counts the layout newtypes. How that set relates to
ffibox's `CCell` is in the `--ffibox` record (`ffibox_layout_not_ccell`,
`ffibox_ccell_not_layout`).

A layout newtype's memory is C's when it is reached through a C pointer, so a
Rust reference to it asserts `noalias`, `readonly` or validity over memory C
may write. Access goes through the handles instead.

- `ty_wrapper_refs_sanctioned` and `ty_wrapper_refs_smell` partition
  the `&W` / `&mut W` positions in function signatures (the receiver included).
  Sanctioned are the accessors `as_ref` / `as_mut`, which hand out borrowed
  handles over a Rust-owned value, and methods of impls of the standard value
  traits `Clone`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash` and `Debug`,
  derived or not. The smell should be 0.
- `ty_wrapper_refs_body_smell` counts the same hazard inside function
  bodies: an expression that forms a reference to a layout wrapper from a raw
  pointer -- `&*p`, `&mut *p`, `&(*p).f` (casts included), an autoref through
  `*p` for a `&self` method, or a call to a function from another crate that
  takes a raw pointer or `NonNull` and returns a type holding `&W`
  (`p.as_ref()`, `NonNull::as_ref`, `slice::from_raw_parts`). Calls to the
  crate's own functions are not counted at the call site; their bodies are.
  A `PhantomData<&W>` marker holds no reference and is not counted. Nothing is
  sanctioned: target 0.
- `ty_field_proj_wrapped` counts field accesses `(*p).field` through a raw pointer
  to a wrapped C type or a wrapper, and `ty_field_proj_outside_impl` the subset
  outside any `impl` or trait body. `ty_field_ref_wrapped` counts the references
  `&(*p).field` / `&mut (*p).field` among them; raw borrows (`&raw const`,
  `addr_of!`) are not counted.

- `deref_impl_on_wrapper` counts impls of `core::ops::Deref` or `DerefMut`
  whose `Self` is a wrapper, layout newtype or handle. Such an impl turns every
  `*w` and auto-deref into a reference to its target, typically the C object,
  outside the handles. Nothing is sanctioned: target 0.

Read these together with `ty_wrapper_newtypes`; when there are no wrapper
newtypes, zero is vacuous. The driver cannot tell a pointer to C memory from
one to a Rust-owned value, so a site means "check where this pointer comes
from".

## ffibox surface

`--ffibox` adds an `ffibox` record, `{"counts": {counter: N}, "by": {counter:
{key: N}}}`: each counter's total, and its breakdown by ffibox type, handle
kind or trait. Every counter is present, zeros included, and each takes
`--sites` alongside `--ffibox`. `_pub` / `_priv` is the effective visibility of
the function for a signature position, and of the implementing type for an
impl.

Signature positions, parameters and return types, nested ones included as for
raw pointers (`Option<CBox<T>>` is one `CBox`):

- `ffibox_fn_owners_*`: an ffibox owner (`CBox`, `CArc`, `CVec`, `CStrBox`,
  `CVal`), keyed by type. Aliases are resolved, so `type FooBox = CBox<..>` is
  a `CBox`.
- `ffibox_fn_handles_*`: an ffibox-based borrowed handle: one of the crate's
  own, keyed `Ref`, `Mut` or `Locked` (the types its `impl CCell` binds to
  `Ref` / `Mut` and its `impl CGuarded` binds to `Locked`, read off the impls
  rather than the names), or one of ffibox's borrowed views, keyed by type
  (`CSlice`, `CSliceMut`, `CBorrowedPtr`, `CGuardedRef`, `CGuard`). A method's
  receiver counts here when it is such a handle, since that is where a C
  function's borrowed `T *` lands.
- `non_ffibox_fn_owner_*`: one of the crate's own owners, keyed by type: a
  crate-defined type with an `impl Drop` that no ffibox macro emitted (the
  `drop_impl` types). Together with `ffibox_fn_*` it says how much of the
  ownership an API hands out goes through ffibox and how much does not.
  (`ffibox_fn_owners_*` is its ffibox counterpart.)
- `non_ffibox_fn_borrow_*`: one of the crate's other borrowed types, keyed by
  type: a crate-defined type with a lifetime parameter of its own that is
  neither one of its `CCell` / `CGuarded` handles nor one of its own owners.
  These are hand-written handles, iterators and views; the key names them, so
  an iterator is told from a handle written instead of a `CCell` one. A
  method's receiver of such a type counts here too.
- `std_fn_borrow_*`: a reference to a standard borrowed view, keyed `&CStr`,
  `&str`, `&mut str`, `&[T]` or `&mut [T]` (nested ones included). A slice of
  elements implementing ffibox's `CPlainElem` (primitives, plain newtypes,
  `MaybeUninit<T>`, raw pointers, arrays of those) is a plain buffer, the
  expected shape, and is keyed `&[CPlainElem]` / `&mut [CPlainElem]` apart. References
  to the crate's layout types are `ty_wrapper_refs_*` instead.

Each splits by the fn's visibility, `_pub` and `_priv`. The
functions read are free functions, inherent methods and the crate's own trait
declarations. A trait impl's methods are left out, since the trait fixes their
signatures. A method's `self` receiver counts only when it is a borrowed handle
(`ffibox_fn_handles_*` or `non_ffibox_fn_borrow_*`): `&self` on an owner or a
plain value borrows a Rust value, not a C object, and is skipped.

The `*_ty_*` families (`ffibox_ty_owners_*`, `ffibox_ty_handles_*`,
`non_ffibox_ty_owner_*`, `non_ffibox_ty_borrow_*`, `std_ty_borrow_*`) count
the same kinds in the fields of the structs, unions and enums the crate
defines, `_pub` / `_priv` by the type's visibility as for `raw_ptr_ty_*`:
what the crate's types hold, where the `*_fn_*` families are what its fns take
and return.

Trait impls, counted as distinct crate-defined types per trait, so a type
implementing `From<A>` and `From<B>` counts once for `From`:

- `ffibox_impl_macro` / `ffibox_impl_manual`: types implementing each ffibox
  trait (`CCell`, `CDrop`, `CRefClone`, `CDupClone`, `CGuarded`, ..), keyed by
  trait, split by whether an ffibox macro (`define_ctype!`, `impl_cdrop!`, ..)
  emitted the impl. A lifecycle policy implements `CDrop<T>` and the like, so
  it is the policy type that counts here, not the layout type.
- `ffibox_define_ctype_macro` / `ffibox_define_ctype_manual`: the crate's
  layout types, its `CCell` implementors, keyed by type, split by whether
  `define_ctype!` emitted the `CCell` impl or it was written by hand.
- `ffibox_ccell_not_layout` / `ffibox_layout_not_ccell`: the crate's types,
  keyed by type, that implement `CCell` without being layout newtypes by shape
  (a wrapper without the layout it claims), and the layout newtypes that do
  not implement `CCell` (wrappers written outside ffibox).
- `drop_impl`: crate-defined types with an `impl Drop` that no ffibox macro
  emitted, keyed by type. Each is an owner written instead of using ffibox's
  `CBox` / `CArc` / `CVec`, so it deserves a look.
- `clone_impl`: crate-defined types with a hand-written `impl Clone`, neither
  derived nor emitted by an ffibox macro, keyed by type. A derived `Clone`
  copies field by field; a hand-written one is a decision about how the C
  object is copied, which ffibox's clone policies (`CDupClone`, `CRefClone`,
  ..) otherwise make.

Impls for a type the crate does not define, or for a reference or other
non-ADT type, are not counted. The compiler's `TrivialClone` and
`StructuralPartialEq` marker impls, which a `#[derive]` adds, are skipped.

## Counter sites

`--sites COUNTER [COUNTER ...]` (or `--sites all`) adds a `sites` record beside
`counts`, with one list per named counter: where that counter's increments are
in the source, as `[{"file": .., "count": N, "lines": [..]}]` per file. `count`
is the number of increments in that file, so a counter's per-file counts sum to
its value in `counts`; `lines` are the distinct lines they fell on, sorted. A
signature position (raw/void pointer, `unsafe fn`, `ty_wrapper_refs_*`) is
sited at its function's signature line; a block, dereference, projection,
reference or call at the expression. A site inside macro output
(`define_ctype!`, `#[derive]`) is the line in the measured crate that invoked
the macro. Only counters that count source locations take `--sites`: the line
and statement totals (`code_lines`, `total_stmts`, `unsafe_block_*lines`,
`unsafe_block_stmts`) have none.

## Known limitations

- **References into C memory the counters miss.** `ty_field_ref_wrapped` matches
  only `&(*p).field` one field deep, so `&(*p).a.b` and `&(*p).arr[i]` are not
  counted; an autoref on a field (`(*p).field.method()` with `&self`) is not
  counted; and a reference to the C type itself (`&*p` with
  `p: *const ffi::T`, or `NonNull<ffi::T>::as_ref`) is counted by no counter,
  since `ty_wrapper_refs_*` only cover wrapper types. See `docs/TODO.md`.
- **Signatures and fields only for pointer positions.** Raw-pointer, `c_void`
  and `ty_wrapper_refs_*` signature counters read the parameter and return
  types of functions with bodies; raw-pointer and `c_void` positions also
  include struct and union fields. Raw pointers in locals, casts, closure parameters, enum variants and
  statics are not positions, `NonNull` is never one, and a trait method
  declared without a default body is not counted.
- **Pointer origin.** No counter can tell C-owned memory from Rust-owned memory
  behind a pointer.
