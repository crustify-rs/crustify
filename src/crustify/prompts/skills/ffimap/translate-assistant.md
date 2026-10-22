<!-- SKILL -->

At batch, wave and campaign end, record an unseeded ffimap scan of the unsafe and FFI
surface in the respective artifact directory: a batch's in the run dir of the run that
landed it, a wave's in `crustify/artifacts/waves/wave-<index>/`, and the campaign's in
`crustify/artifacts/`. A module's end is the scan of its last wave.

```bash
ffimap <workdir> --json > <artifact dir>/ffimap.json
```

It counts what the safe crate itself defines. The public unsafe surface is
`unsafe_fns_pub`; the raw pointers on its safe public interface are
`raw_ptr_ty_pub_fields_pub` (in public fields of public types) plus `raw_ptr_fn_pub_safe`
(in the signatures of public safe fns). Use `--sites` with those counters to list where
they are.
