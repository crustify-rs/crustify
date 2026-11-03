# ffimap › verification/reviewing

## Objectives

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
