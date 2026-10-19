<!-- SKILL -->

### 1. Analysis

Locate the fishy sites with the scan, and keep those in your workset: the code your
commits add or change, or your modules and the types, trait impls and functions they
name. They are starting points, not your whole review: ffimap is neither complete nor
sound, so review beyond them.

```bash
ffimap <workdir> --json --sites <counter> ...
```

`--sites` lists where each named counter's increments are.

- For `unsafety`: `unsafe_fns_pub`, the public `unsafe fn`s; `raw_ptr_ty_pub_fields_pub`,
  the raw pointers in public fields of public types; and `raw_ptr_fn_pub_safe`, the raw
  pointers in the signatures of public safe fns.
- For `contracts`: `unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`, whose `# Safety`
  obligations you evaluate.
- For `ub`, review these smells first, in this order: `c_type_borrow_non_sanctioned`,
  references into C memory anywhere in the crate, `Deref` impls included, and
  `c_type_borrow_generic`, the ones generic code forms from a raw pointer, and
  `raw_ptr_as_slice_borrow`, the `&[T]`, `&str` and `&CStr` formed from one;
  `unsafe_send_impl` and `unsafe_sync_impl`, thread-safety claims to check against the C
  library's contract; lifetime annotations formed in unsafe blocks; `raw_ptr_fn_pub_safe`, `void_ptr_fn_pub_safe`,
  `raw_ptr_ty_pub_fields_pub` and `void_ptr_ty_pub_fields_pub`, raw pointers a consumer
  can set, unsound when a safe path dereferences or frees them; `raw_ptr_derefs_wr`, then
  `raw_ptr_derefs_rd`, the dereferences whose validity the implementer vouches for, first
  where a write meets a reference into the same object; and `drop_impl` and `clone_impl`,
  hand-written teardown and copies.
