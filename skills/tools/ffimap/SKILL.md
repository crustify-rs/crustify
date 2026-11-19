---
name: ffimap
description: "Deterministic counts and sites of a Rust crate's unsafe and FFI surface, per crate and per region, and of its consumer-facing API. Read before measuring the unsafe surface for crustify/STATUS.md or the report, before a component's work is merged, and when reviewing for unsafety, contracts or UB."
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

## Scanning

Every scan names the crate's seams, the functions that hand a value between its wrapper and
its raw form, so that each counter's `of_which.seam` share tells that plumbing apart from
the pointer management a consumer of the safe API faces: ffibox's handle seams `as_ptr`,
`as_mut_ptr`, `as_void_ptr`, `from_ptr` and `from_void_ptr`, the ownership hand-offs
`from_raw_parts`, `into_raw_parts`, `into_raw`, `from_c`, `into_c` and `as_c_ptr`, the
adoption of a raw C value, `from_raw`, and the view of a C object as another, `as_object`.
A crate built on ffibox is scanned with `--ffibox`, and its `-sys` crates are named with
`--sys-crates`:

```bash
ffimap <workdir> --ffibox --sys-crates <the -sys crates> --regions ffi_import,ffi_export \
    --seams as_ptr,as_mut_ptr,as_void_ptr,from_ptr,from_void_ptr,from_raw_parts,into_raw_parts,into_raw,from_c,into_c,as_c_ptr,from_raw,as_object \
    > <file>.json
```

Raw bindings that are a module of the crate, not a crate of their own, laid out and
generated as [`bindgen`](../../rust/bindgen/SKILL.md) describes, are named to `--sys-crates`
by their path, `crate::<path>`, beside the `-sys` crates that remain. A named module joins
the inventory and leaves every other counter, as a `-sys` crate does. Left unnamed, its C
types and functions are in no inventory, the counts that read it are taken over the other
crates' alone, and the generated code counts as the crate's own, all with no error. A module
that holds hand-written code beside its declarations is left unnamed, since naming it would
take that code out of the scan.

A scan names with `--features` every export feature the build enables, as the
[conventions](../../rust/conventions/SKILL.md)' Export features section names them, so that
the `ffi_export` gateways compiled under them are counted, and names the crate's unsafe
regions with `--regions`, as the conventions' Unsafe regions section names them.

Scan the library alone, never with `cargo check --all-targets` over a crate whose
dev-dependencies enable test-only features of the crate itself, such as a
`test-internals` feature that makes internals public: ffimap then counts those internals
as public API, and the public counters overstate the surface.

Two scans are compared only when they name the same seams, regions and features.

## Counters

Its counters form one tree, each named by its dotted path into the scan's `counts`, as
ffimap's `docs/schema.md` describes. A metric is a counter, or a combination of counters
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
- `ty.impl_trait.of_which.std.send.{pub,priv}` and `ty.impl_trait.of_which.std.sync.{pub,priv}`,
  each an unchecked assertion that a value may move to or be shared with another thread;
- `raw_ptr.deref.wr` and `raw_ptr.deref.rd`, raw-pointer writes and reads, each a pointer
  the implementer vouches is non-null, aligned, live, initialized and unaliased by a live
  reference; and
- `ty.storing_raw_ptr.of_which.impl_drop.{pub,priv}` and
  `ty.storing_raw_ptr.of_which.impl_clone.{pub,priv}`, the types that hold a raw pointer and
  tear it down or copy it by hand, and `ty.storing_raw_ptr.of_which.none.{pub,priv}`, those
  that declare nothing about it. Each of these five also has a `.total`, the sum of its two
  leaves, which is no leaf for `--sites`.

ffimap is neither complete nor sound: its sites are where review starts, not all it
covers. It does not count the lifetimes formed inside `unsafe` blocks, such as a reference
or lifetime-annotated handle made from a raw pointer by `&*p`, `from_ptr`, `from_raw` or
`from_raw_parts`, or changed by a `transmute`: those are found in the source.

What follows is what ffimap adds to each kind of work.

## Measuring the unsafe surface

ffimap is how the agent measures the unsafe surface, for `crustify/STATUS.md`'s per-file
counters and for the report. Each file's row takes, from a scan's sites:

- its unsafe blocks, those inside each region, `code.unsafe_block.of_which.region.<region>`,
  and those outside every region, `code.unsafe_block.of_which.outside_regions`;
- its `unsafe fn`s, `fn.unsafe.pub` and `fn.unsafe.priv`; and
- the raw pointers on its public interface: `raw_ptr.field.pub`,
  `raw_ptr.fn_sig_arg.safe.pub`, `raw_ptr.fn_sig_ret.safe.pub`,
  `raw_ptr.fn_sig_arg.unsafe.pub` and `raw_ptr.fn_sig_ret.unsafe.pub`.

Count the sites per file from `--sites`, since `counts` sums the whole crate;
`code.unsafe_block.total` and `code.loc.unsafe` give the crate's totals. Take every measurement with the same seams, regions and features, so that the
numbers of two dates compare, and remeasure a file when its component changes.

## Merging a component

Before a component's work is merged, a scan with `--sites fn.unsafe.pub raw_ptr.field.pub
raw_ptr.fn_sig_arg.safe.pub raw_ptr.fn_sig_ret.safe.pub` lists the public `unsafe fn`s and
the raw pointers on the safe public interface, and each of those sites that the
component's change adds and that a safe variant could replace is fixed. Its `--sites` also
name the unsafe code outside both regions, `code.unsafe_block.of_which.outside_regions`,
another crate's macro expansions included, which the `unsafe_code` lint misses, and
`fn.unsafe.of_which.outside_regions.pub` and `.priv`: outside the raw bindings, each of
those sites in the change is moved into its region.

## API stability

`ffimap api` measures a safe crate's consumer-facing API per C item, from rustdoc JSON, as
its `docs/api.md` describes, read in full before its first use. A C item is the
`<kind>::<path>` of a `Wraps` or `Replaces` anchor, as the conventions' Anchors section
places them. Its surface is every stand-in the anchor names and the handles and owners tied
to it: the methods every form offers, its reborrows and dereferences, and the traits a
consumer can use, never a form's raw access or seams. Generate the safe crate's rustdoc
JSON before and after a change, with a nightly whose `format_version` the tool supports,
and ffibox's, with private items, for the contracts of the forms it defines:

```bash
cargo +<nightly> rustdoc -p <crate> --lib -- -Z unstable-options --output-format json
ffimap api diff <base>.json <tree>.json --dep <ffibox>.json --items "<the C items>" --format json
```

Each item comes out `kept`, `extended`, `changed`, `removed` or `new`, with its anchor's
move from `Wraps` to `Replaces` where a port made it. A `changed` or `removed` item is a
change Rust consumers see, which the report names.

## Reviewing

A review locates the sites of its objectives with a scan, `--sites` with their counters,
and keeps those in the code it reviews. The sites are where the reading starts, as
[`reviewing`](../../verification/reviewing/SKILL.md) describes, and a module the scan
reports nothing in is still read.

- Avoidable unsafe code: `fn.unsafe.pub`, `raw_ptr.field.pub`,
  `raw_ptr.fn_sig_arg.safe.pub` and `raw_ptr.fn_sig_ret.safe.pub`.
- Safety documentation: `fn.unsafe.pub`, `raw_ptr.fn_sig_arg.unsafe.pub` and
  `raw_ptr.fn_sig_ret.unsafe.pub`, whose `# Safety` obligations are evaluated.
- Undefined behaviour: these smells first, in this order:
  1. references into C memory: the references to a cell outside its sanctioned positions,
     `ty.ffibox.wrapper.as.borrowed.std.{pub,priv}` less those shares, and to a raw C
     struct, `ty.ffibox.sys.as.borrowed.std.{pub,priv}`, then
     `raw_ptr.casted_to.std.{borrow,slice,string}`;
  2. thread-safety claims, `ty.impl_trait.of_which.std.send.{pub,priv}` and
     `ty.impl_trait.of_which.std.sync.{pub,priv}`, checked against the C library's
     contract: a data race is reachable from safe code when the library does not allow
     what they assert;
  3. the lifetimes formed inside `unsafe` blocks, found in the source: unsound when the
     handle can outlive the owner of the memory or the point at which C frees or
     invalidates it;
  4. raw pointers a consumer can set, `raw_ptr.fn_sig_arg.safe.pub` and
     `raw_ptr.field.pub`, with their `of_which.void` shares: unsound when a safe path
     dereferences or frees what the consumer passed or stored;
  5. raw-pointer dereferences, `raw_ptr.deref.wr` then `raw_ptr.deref.rd`: first in the
     modules that also hold references into C memory, where a write may invalidate a
     reference, and outside a type's accessors; and
  6. hand-written teardown and copies, `ty.storing_raw_ptr.of_which.impl_drop.{pub,priv}`
     and `ty.storing_raw_ptr.of_which.impl_clone.{pub,priv}`.

A site of `ty.storing_raw_ptr.of_which.impl_drop`, `.impl_clone`,
`ty.impl_trait.of_which.std.send` or `.sync`, at either leaf, is a trait impl, named
`Drop for <type>`, `Clone for <type>`, `Send for <type>` or `Sync for <type>`.

A scan that fails, that covers part of the crate, or that the source contradicts is a
defect in ffimap: file it in `crustify/reviews/` with its reproducer, and review from the
source.
