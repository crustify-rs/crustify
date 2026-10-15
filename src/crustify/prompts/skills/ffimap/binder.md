<!-- SKILL -->

Before landing, run the scan on the safe crate and fix any public `unsafe fn` or raw
pointer on the safe public interface that you might have missed. Focus only on the sites
that belong to your changeset.

```bash
crustify ffimap <workdir> --json --sites unsafe_fns_pub raw_ptr_ty_pub_fields_pub raw_ptr_fn_pub_safe
```

`--sites` lists the public `unsafe fn`s, the raw pointers in public fields of public types,
and the raw pointers in the signatures of public safe fns.
