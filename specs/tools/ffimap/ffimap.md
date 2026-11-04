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
`as_mut_ptr`, `as_void_ptr`, `from_ptr` and `from_void_ptr`, and the ownership hand-offs
`from_raw_parts`, `into_raw_parts`, `from_c`, `into_c` and `as_c_ptr`. A crate built on
ffibox is scanned with `--ffibox`, and its `-sys` crates are named with `--sys-crates`:

```bash
ffimap <workdir> --ffibox --sys-crates <the -sys crates> \
    --seams as_ptr,as_mut_ptr,as_void_ptr,from_ptr,from_void_ptr,from_raw_parts,into_raw_parts,from_c,into_c,as_c_ptr \
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
