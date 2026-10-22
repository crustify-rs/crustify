<!-- SKILL -->

## workflows/audit › Worksets

Plan the audit's worksets from an ffimap scan of the crate, run once each build
configuration you audit is in place:

```bash
ffimap <workdir> --json --sites <counter> ...
```

`--sites` lists where each named counter's increments are. ffimap counts what the build
compiles, so a file outside every configuration you scan has no sites: plan it from the
source instead.

For `ub`, review the modules that hold these smells first, in this order:

1. references into C memory: `c_type_borrow_non_sanctioned`, borrows anywhere in the
   crate, public or private, `Deref` impls included, that assert `noalias`, `readonly` or
   validity over memory C may write, then `c_type_borrow_generic`, the ones generic code
   forms from a raw pointer for every type its callers pick, and `raw_ptr_as_slice_borrow`,
   the `&[T]`, `&str` and `&CStr` formed from a raw pointer, over bytes C must neither
   free nor change while they live;
2. thread-safety claims: `unsafe_send_impl` and `unsafe_sync_impl`, each an unchecked
   assertion that a value may move to or be shared with another thread, a data race
   reachable from safe code when the C library does not allow it;
3. lifetimes formed inside `unsafe` blocks: a reference or lifetime-annotated handle made
   there from a raw pointer, such as `&*p`, `from_ptr`, `from_raw` or `from_raw_parts`
   returning a `Ref<'a>` or a `&'a T`, or a lifetime changed by a `transmute`. The compiler
   ties such a lifetime to nothing: it is whatever the enclosing signature or the use
   picks, and unsound when it lets the handle outlive the owner of the memory or the point
   at which C frees or invalidates it. ffimap does not count them, so find them in the
   source;
4. raw pointers a consumer can set: `raw_ptr_fn_pub_safe`, `void_ptr_fn_pub_safe`,
   `raw_ptr_ty_pub_fields_pub` and `void_ptr_ty_pub_fields_pub`, unsound when a safe path
   dereferences or frees what the consumer passed or stored;
5. raw-pointer dereferences: `raw_ptr_derefs_wr`, then `raw_ptr_derefs_rd`, each a pointer
   the implementer vouches is non-null, aligned, live, initialized and unaliased by a live
   reference; first in the modules that also hold `c_type_borrow_non_sanctioned` sites,
   where a write may invalidate a reference, and outside impls,
   `raw_ptr_derefs_outside_impl`, where it bypasses the type's accessors;
6. hand-written teardown and copies: `drop_impl` and `clone_impl`, owners and copies whose
   handling of a C object requires care.

For `contracts`, review first the modules that hold the crate's unsafe API and its
justifications:
`unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`, the public `unsafe fn`s whose `# Safety`
obligations they evaluate.

Batch the modules by their sites, and, when you split a module, keep a type, trait impl or
function with its sites in one batch. A `drop_impl`, `clone_impl`, `unsafe_send_impl` or
`unsafe_sync_impl` site is a trait impl: name it as `Drop for <type>`, `Clone for <type>`,
`Send for <type>` or `Sync for <type>`. The reviewers run the same scan over their
modules, so the sites need not be passed on. Review the rest of the crate after the smells.
