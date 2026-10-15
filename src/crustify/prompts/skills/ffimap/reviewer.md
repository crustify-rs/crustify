<!-- SKILL -->

A `sites` worklist already names your sites. Otherwise, locate your workset's sites with
the scan, and narrow them to those in your workset:

```bash
ffimap <workdir> --json --ffibox --sites <counter> ...
```

`--sites` lists where each named counter's increments are.

- For `unsafety`: `unsafe_fns_pub`, the public `unsafe fn`s; `raw_ptr_ty_pub_fields_pub`,
  the raw pointers in public fields of public types; and `raw_ptr_fn_pub_safe`, the raw
  pointers in the signatures of public safe fns.
- For `contracts`: `unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`, whose `# Safety`
  obligations you evaluate, and `undocumented_unsafe`, the `unsafe` sites with no
  `// SAFETY:` comment.
- For `ub`, review these smells first: `ty_wrapper_borrow_non_sanctioned`, safe API with
  references to raw wrappers; `raw_ptr_fn_pub_safe`, `void_ptr_fn_pub_safe`,
  `raw_ptr_ty_pub_fields_pub`, `void_ptr_ty_pub_fields_pub` and
  `fn_sig_non_ffibox_handle_pub`, safe API with references that expose or embed raw
  pointers; and `drop_impl`, in the `ffibox` record, hand-written `Drop` impls.
