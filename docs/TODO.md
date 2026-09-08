# TODO

Deferred decisions and follow-up work on the crustify contracts and playbooks.

## Emit type-implementing symbols as inherent methods

A symbol whose first parameter is the type it operates on is currently emitted
as a free function (`conventions.md`, "Functions and FFI names"). Emitting it as
an inherent method on that type instead would read better at call sites —
`commit.message()` over `git_commit_message(commit)` — and needs no
restructuring, since inherent impls are crate-scoped and the handle types are
generated in the same module as their functions.

Measured over the 860 anchored free functions in `libgit2-wrap`, 629 take a
wrapped handle first and could convert:

| first parameter | count | method receiver | lifetime cost |
|---|---:|---|---|
| owned handle (`Foo`, `FooOwned`, `CBox<Foo>`) | 8 | `&self` / `&mut self` | none, elision applies |
| borrowed handle, returns no reference | 441 | `self` or `&mut self` | none |
| borrowed handle, returns a reference | 180 | `self` | must name `'a` |

Two findings decide whether this is worth doing:

- The elision win barely exists here. Rule 3 needs `&self`/`&mut self`, and only
  8 of 629 take an owned handle. The other 621 take copyable `FooRef`/`FooMut`,
  where a by-value `self` receiver does not elide at all (`E0106`).
- Taking `&self` on a borrowed handle to obtain elision is wrong: the returned
  reference binds to the handle's own storage rather than the C object, so it
  cannot outlive the caller's local (`E0515`). The 10 functions that take
  `&mut FooMut<'_>` *and* return a reference are the trap — as `&mut self`
  methods they compile at the definition and fail at the call site.

So the case rests on ergonomics, not on lifetime elision. If adopted, the rule
belongs in `translator-playbook.md` under "Functions and globals", with the
`&self`-on-a-borrowed-handle hazard stated explicitly, and the free-function
clause in `conventions.md` relaxed to defer the shape to the playbook.

Also open: whether existing waves get retrofitted, or the crate carries two
generations of shape side by side.
