<!-- SKILL -->

Plan the audit's worksets from an ffimap scan of the crate, run once each build
configuration you audit is in place:

```bash
ffimap <workdir> --json --ffibox --sites <counter> ...
```

`--sites` lists where each named counter's increments are. ffimap counts what the build
compiles, so a file outside every configuration you scan has no sites: plan it from the
source instead.

For `ub`, review the smells first, in this order, and give the reviewers their sites:

1. safe API with references to raw wrappers: `ty_wrapper_borrow_non_sanctioned`, borrows
   of C memory that assert `noalias`, `readonly` or validity over memory C may write;
2. safe API with references that expose or embed raw pointers: `raw_ptr_fn_pub_safe`,
   `void_ptr_fn_pub_safe`, `raw_ptr_ty_pub_fields_pub`, `void_ptr_ty_pub_fields_pub`, and
   the handles written outside ffibox, `fn_sig_non_ffibox_handle_pub`;
3. hand-written `Drop` impls: `drop_impl`, in the `ffibox` record, owners whose release of
   C resources no ffibox policy vouches for.

For `contracts`, give the reviewers the crate's unsafe API and its justifications:
`unsafe_fns_pub` and `raw_ptr_fn_pub_unsafe`, the public `unsafe fn`s whose `# Safety`
obligations they evaluate, and `undocumented_unsafe`, the `unsafe` sites with no
`// SAFETY:` comment.

Batch the sites as `sites` worksets: each entry is one file of a counter's `sites` record,
`{"counter": .., "file": .., "lines": [..]}`, with `count` dropped and `file` made
relative to the repository. Review the rest of the crate after the smells.
