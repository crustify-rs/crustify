<!-- SKILL -->

At batch, wave, subsystem, and campaign end, record an unseeded ffimap scan of the
unsafe and FFI surface in the respective artifact directory:

```bash
ffimap <workdir> --json > <artifact dir>/ffimap.json
```

It counts what the safe crate itself defines. The public unsafe surface is
`unsafe_fns_pub`; the raw pointers on its safe public interface are
`raw_ptr_ty_pub_fields_pub` (in public fields of public types) plus `raw_ptr_fn_pub_safe`
(in the signatures of public safe fns). Use `--sites` with those counters to list where
they are.

A batch's row in a `Batches: safety audit` table of the dashboard is the change, in each
of the Safety audit's metrics, from the scan of the commit its landing followed to the scan
of its landing.
