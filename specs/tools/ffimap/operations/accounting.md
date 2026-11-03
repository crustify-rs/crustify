# ffimap › operations/accounting

## Landing cells

A batch's row in the dashboard's `Batches: safety audit` table is the change in each of
the Safety audit's metrics, from a scan of the tip its landing rebased onto to a scan of
the tree it lands.

## Records

An unseeded scan of the unsafe and FFI surface is recorded at each batch's, wave's and
the campaign's end, as `ffimap.json` in its artifact directory: a batch's in the run dir
of the run that landed it, a wave's in `crustify/artifacts/waves/wave-<index>/`, and the
campaign's in `crustify/artifacts/`. A module's end is the scan of its last wave.
