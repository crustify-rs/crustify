<!-- SKILL -->

<!-- OBJECTIVE unsafety -->
Locate your workset's public unsafe surface with the scan, and narrow its sites to those
that belong to your workset:

```bash
crustify ffimap <workdir> --json --sites unsafe_fns_pub raw_ptr_ty_pub_fields_pub raw_ptr_fn_pub_safe
```

`--sites` lists the public `unsafe fn`s, the raw pointers in public fields of public types,
and the raw pointers in the signatures of public safe fns.
<!-- /OBJECTIVE -->
