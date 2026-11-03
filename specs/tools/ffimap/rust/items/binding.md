# ffimap › rust/items/binding

## Safe boundary

Before a batch lands, a scan with
`--sites unsafe_fns_pub raw_ptr_ty_pub_fields_pub raw_ptr_fn_pub_safe` lists the public
`unsafe fn`s and the raw pointers on the safe public interface, and each of those sites
that belongs to the batch's changeset and that a safe variant could replace is fixed.
