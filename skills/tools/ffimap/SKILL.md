---
name: ffimap
description: "Deterministic counts and sites of a Rust crate's unsafe and FFI surface. Read before a batch lands (its safe-boundary scan and safety-audit cells), before planning an audit's worksets, and when reviewing for unsafety, contracts or UB."
---

# ffimap

ffimap maps a Rust crate's FFI and unsafe surface deterministically: a rustc driver over
HIR and typeck counts unsafe blocks and fns, raw and void pointers by position and
visibility, FFI calls and wrapper use. No model is involved, so two runs over one tree
agree exactly. Its `--help` lists its flags and counters.

It counts what the build compiles of the safe crate itself, and prints one JSON document:

```bash
ffimap <workdir> > <file>.json
```

Every scan names the crate's seams, the functions that hand a value between its wrapper and
its raw form, so that each counter's `of_which.seam` share tells that plumbing apart from
the pointer management a consumer of the safe API faces: ffibox's handle seams `as_ptr`,
`as_mut_ptr`, `as_void_ptr`, `from_ptr` and `from_void_ptr`, the ownership hand-offs
`from_raw_parts`, `into_raw_parts`, `from_c`, `into_c` and `as_c_ptr`, the adoption of a raw C
value, `from_raw`, and the view of a C object as another, `as_object`. A crate built on
ffibox is scanned with `--ffibox`, and its `-sys` crates are named with `--sys-crates`:

```bash
ffimap <workdir> --ffibox --sys-crates <the -sys crates> \
    --seams as_ptr,as_mut_ptr,as_void_ptr,from_ptr,from_void_ptr,from_raw_parts,into_raw_parts,from_c,into_c,as_c_ptr,from_raw,as_object \
    > <file>.json
```

Two scans are compared only when they name the same seams.

`--sites <counter> ...` also lists where each named counter's increments are. The
counters that recur:

- `unsafe_fns_pub`, the public `unsafe fn`s, the crate's public unsafe surface, and
  `raw_ptr_fn_pub_unsafe`, the raw pointers in their signatures;
- `raw_ptr_ty_pub_fields_pub`, the raw pointers in public fields of public types, and
  `raw_ptr_fn_pub_safe`, those in the signatures of public safe fns: together, the raw
  pointers on the safe public interface; and `void_ptr_ty_pub_fields_pub` and
  `void_ptr_fn_pub_safe`, the type-erased ones among them;
- `c_type_borrow_non_sanctioned`, references into C memory outside the sanctioned handle
  positions, `Deref` impls included, which assert `noalias`, `readonly` or validity over
  memory C may write; `c_type_borrow_generic`, those generic code forms from a raw pointer
  for every type its callers pick; and `raw_ptr_as_slice_borrow`, the `&[T]`, `&str` and
  `&CStr` formed from a raw pointer, over bytes C must neither free nor change while they
  live;
- `unsafe_send_impl` and `unsafe_sync_impl`, each an unchecked assertion that a value may
  move to or be shared with another thread;
- `raw_ptr_derefs_wr` and `raw_ptr_derefs_rd`, raw-pointer writes and reads, each a
  pointer the implementer vouches is non-null, aligned, live, initialized and unaliased by
  a live reference, and `raw_ptr_derefs_outside_impl`, those that bypass a type's
  accessors; and
- `drop_impl` and `clone_impl`, hand-written teardown and copies.

ffimap is neither complete nor sound: its sites are where review starts, not all it
covers. It does not count the lifetimes formed inside `unsafe` blocks, such as a reference
or lifetime-annotated handle made from a raw pointer by `&*p`, `from_ptr`, `from_raw` or
`from_raw_parts`, or changed by a `transmute`: those are found in the source.

What follows is how ffimap serves each stage: each section names the skill and section it
adds to, and states only what ffimap adds there.

## Binding and porting

### Binding › Safe boundary

Before a batch lands, a scan with
`--sites unsafe_fns_pub raw_ptr_ty_pub_fields_pub raw_ptr_fn_pub_safe` lists the public
`unsafe fn`s and the raw pointers on the safe public interface, and each of those sites
that belongs to the batch's changeset and that a safe variant could replace is fixed.

## Accounting

### Accounting › Landing cells

A batch's row in the dashboard's `Batches: safety audit` table is the change in each of
the Safety audit's metrics, from a scan of the tip its landing rebased onto to a scan of
the tree it lands.

### Accounting › Records

An unseeded scan of the unsafe and FFI surface is recorded at each batch's, wave's and
the campaign's end, as `ffimap.json` in its artifact directory: a batch's in the run dir
of the run that landed it, a wave's in `crustify/artifacts/waves/wave-<index>/`, and the
campaign's in `crustify/artifacts/`. A module's end is the scan of its last wave.

## Reviewing

### Reviewing › Objectives

A review locates the sites of its objectives with a scan, `--sites` with their counters,
and keeps those in its workset: the code its commits add or change, or its modules and
the types, trait impls and functions they name.

- `unsafety`: `unsafe_fns_pub`, `raw_ptr_ty_pub_fields_pub` and `raw_ptr_fn_pub_safe`.
- `contracts`: `unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`, whose `# Safety` obligations
  are evaluated.
- `ub`: these smells first, in this order:
  1. references into C memory: `c_type_borrow_non_sanctioned`, then
     `c_type_borrow_generic` and `raw_ptr_as_slice_borrow`;
  2. thread-safety claims, `unsafe_send_impl` and `unsafe_sync_impl`, checked against the
     C library's contract: a data race is reachable from safe code when the library does
     not allow what they assert;
  3. the lifetimes formed inside `unsafe` blocks, found in the source: unsound when the
     handle can outlive the owner of the memory or the point at which C frees or
     invalidates it;
  4. raw pointers a consumer can set, `raw_ptr_fn_pub_safe`, `void_ptr_fn_pub_safe`,
     `raw_ptr_ty_pub_fields_pub` and `void_ptr_ty_pub_fields_pub`: unsound when a safe
     path dereferences or frees what the consumer passed or stored;
  5. raw-pointer dereferences, `raw_ptr_derefs_wr` then `raw_ptr_derefs_rd`: first in the
     modules that also hold `c_type_borrow_non_sanctioned` sites, where a write may
     invalidate a reference, and outside impls, `raw_ptr_derefs_outside_impl`; and
  6. hand-written teardown and copies, `drop_impl` and `clone_impl`.

## Audit

### Audit workflow › Worksets

The audit's worksets are planned from a scan of the crate, run once each build
configuration it audits is in place, with `--sites` over the counters of its objectives.
A file outside every configuration scanned has no sites, and is planned from its source.

For `ub`, the modules that hold the smells ffimap's review guidance lists for `ub` are
reviewed first, in that order; for `contracts`, those that hold the crate's unsafe API and
its justifications, `unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`. The rest of the crate
follows the smells.

The modules are batched by their sites, and a module that is split keeps a type, trait
impl or function with its sites in one batch. A `drop_impl`, `clone_impl`,
`unsafe_send_impl` or `unsafe_sync_impl` site is a trait impl, named `Drop for <type>`,
`Clone for <type>`, `Send for <type>` or `Sync for <type>`. Each review runs the same scan
over its own modules, so the sites are not passed on.
