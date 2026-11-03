# ffimap › workflows/audit

## Worksets

The audit's worksets are planned from a scan of the crate, run once each build
configuration it audits is in place, with `--sites` over the counters of its objectives.
A file outside every configuration scanned has no sites, and is planned from its source.

For `ub`, the modules that hold the smells ffimap's review guidance lists for `ub` are
reviewed first, in that order; for `contracts`, those that hold the crate's unsafe API and
its justifications, `unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`. The rest of the crate
follows the smells.

The modules are batched by their sites, and a module that is split keeps a type, trait
impl or function with its sites in one batch. A `drop_impl`, `clone_impl`,
`unsafe_send_impl` or `unsafe_sync_impl` site is a trait impl, named `Drop for <type>`,
`Clone for <type>`, `Send for <type>` or `Sync for <type>`. Each review runs the same scan
over its own modules, so the sites are not passed on.
