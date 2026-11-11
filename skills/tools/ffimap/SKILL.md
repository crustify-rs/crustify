---
name: ffimap
description: "Deterministic counts and sites of a Rust crate's unsafe and FFI surface. Read before a batch lands (its safe-boundary scan and safety-audit cells), before planning an audit's worksets, and when reviewing for unsafety, contracts or UB."
---

# ffimap

ffimap maps a Rust crate's FFI and unsafe surface deterministically: a rustc driver over
HIR and typeck counts unsafe blocks and fns, raw and void pointers by position and
visibility, FFI calls and wrapper use. No model is involved, so two runs over one tree
agree exactly. Its `--help` lists its flags, and its `docs/schema.md`, read in full before
its first scan, its counters and how a report combines them.

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

Its counters form one tree, each named by its dotted path into the scan's `counts`, as
ffimap's `docs/schema.md` describes; a metric is a counter, or a combination of counters
that schema allows: a partition's leaves summed, a share read against the record it cuts,
or subtracted from it. `--sites <counter> ...` also lists where each named counter's
increments are, and takes leaves only, such as `fn.unsafe.pub`; the workspace is named
before it. The counters that recur:

- `fn.unsafe.pub`, the public `unsafe fn`s, the crate's public unsafe surface, of which
  `fn.unsafe.of_which.other.pub` are those neither a trait nor a seam required; and
  `raw_ptr.fn_sig_arg.unsafe.pub` and `raw_ptr.fn_sig_ret.unsafe.pub`, the raw pointers in
  their signatures;
- `raw_ptr.field.pub`, `raw_ptr.fn_sig_arg.safe.pub` and `raw_ptr.fn_sig_ret.safe.pub`, the
  raw pointers in public fields and in the signatures of public safe fns, together
  `raw_ptr.total.safe.pub`, the raw pointers on the safe public interface; and their
  `of_which.void` shares, the type-erased ones among them;
- `ty.ffibox.wrapper.as.borrowed.std.{pub,priv}`, the references to a cell, less their
  `of_which.self_in_ref_accessor` and `of_which.self_in_trait_impl` shares, the positions
  ffibox sanctions: references to C memory where a handle belongs, which assert `noalias`,
  `readonly` or validity over memory C may write; `ty.ffibox.sys.as.borrowed.std`, the same
  of the raw C structs; and `raw_ptr.casted_to.std.{borrow,slice,string}`, the borrows,
  slices and strings formed from a raw pointer, over bytes C must neither free nor change
  while they live;
- `ty.impl_trait.of_which.std.send` and `ty.impl_trait.of_which.std.sync`, each an unchecked
  assertion that a value may move to or be shared with another thread;
- `raw_ptr.deref.wr` and `raw_ptr.deref.rd`, raw-pointer writes and reads, each a pointer
  the implementer vouches is non-null, aligned, live, initialized and unaliased by a live
  reference; and
- `ty.storing_raw_ptr.of_which.impl_drop` and `ty.storing_raw_ptr.of_which.impl_clone`, the
  types that hold a raw pointer and tear it down or copy it by hand, and
  `ty.storing_raw_ptr.of_which.none`, those that declare nothing about it.

ffimap is neither complete nor sound: its sites are where review starts, not all it
covers. It does not count the lifetimes formed inside `unsafe` blocks, such as a reference
or lifetime-annotated handle made from a raw pointer by `&*p`, `from_ptr`, `from_raw` or
`from_raw_parts`, or changed by a `transmute`: those are found in the source.

What follows is how ffimap serves each stage: each section names the skill and section it
adds to, and states only what ffimap adds there.

## Binding and porting

### Binding › Safe boundary

Before a batch lands, a scan with `--sites fn.unsafe.pub raw_ptr.field.pub
raw_ptr.fn_sig_arg.safe.pub raw_ptr.fn_sig_ret.safe.pub` lists the public
`unsafe fn`s and the raw pointers on the safe public interface, and each of those sites
that belongs to the batch's changeset and that a safe variant could replace is fixed.
<!-- TODO: ffimap counts the unsafe blocks of `ffi_export` regions,
`code.unsafe_block.of_which.ffi_export`, but not yet those of `ffi_import`, nor the unsafe
code a macro of another crate expands outside both regions, which the `unsafe_code` lint
misses: until it does, those invocations are found in the source. -->

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

- `unsafety`: `fn.unsafe.pub`, `raw_ptr.field.pub`, `raw_ptr.fn_sig_arg.safe.pub` and
  `raw_ptr.fn_sig_ret.safe.pub`.
- `contracts`: `fn.unsafe.pub`, `raw_ptr.fn_sig_arg.unsafe.pub` and
  `raw_ptr.fn_sig_ret.unsafe.pub`, whose `# Safety` obligations are evaluated.
- `ub`: these smells first, in this order:
  1. references into C memory: the references to a cell outside its sanctioned positions,
     `ty.ffibox.wrapper.as.borrowed.std.{pub,priv}` less those shares, and to a raw C
     struct, `ty.ffibox.sys.as.borrowed.std.{pub,priv}`, then
     `raw_ptr.casted_to.std.{borrow,slice,string}`;
  2. thread-safety claims, `ty.impl_trait.of_which.std.send` and `.sync`, checked against
     the C library's contract: a data race is reachable from safe code when the library
     does not allow what they assert;
  3. the lifetimes formed inside `unsafe` blocks, found in the source: unsound when the
     handle can outlive the owner of the memory or the point at which C frees or
     invalidates it;
  4. raw pointers a consumer can set, `raw_ptr.fn_sig_arg.safe.pub` and
     `raw_ptr.field.pub`, with their `of_which.void` shares: unsound when a safe path
     dereferences or frees what the consumer passed or stored;
  5. raw-pointer dereferences, `raw_ptr.deref.wr` then `raw_ptr.deref.rd`: first in the
     modules that also hold references into C memory, where a write may invalidate a
     reference, and outside a type's accessors; and
  6. hand-written teardown and copies, `ty.storing_raw_ptr.of_which.impl_drop` and
     `.impl_clone`.

## Audit

### Audit workflow › Worksets

The audit's worksets are planned from a scan of the crate, run once each build
configuration it audits is in place, with `--sites` over the counters of its objectives.
A file outside every configuration scanned has no sites, and is planned from its source.

For `ub`, the modules that hold the smells ffimap's review guidance lists for `ub` are
reviewed first, in that order; for `contracts`, those that hold the crate's unsafe API and
its justifications, the `contracts` counters above. The rest of the crate
follows the smells.

The modules are batched by their sites, and a module that is split keeps a type, trait
impl or function with its sites in one batch. A site of `ty.storing_raw_ptr.of_which.impl_drop`,
`.impl_clone`, `ty.impl_trait.of_which.std.send` or `.sync` is a trait impl, named
`Drop for <type>`, `Clone for <type>`, `Send for <type>` or `Sync for <type>`. Each review
runs the same scan over its own modules, so the sites are not passed on.
