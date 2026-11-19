---
name: anchors
description: "How the Rust records which C item each Rust item stands in for: the Wraps and Replaces doc anchors, their rustdoc aliases, and which item carries them. Read before writing any public item that stands in for a C item, and when reviewing one."
---

# Anchors

The Rust item that stands in for each C item is annotated, and those annotations are the
only record that an item was translated.

An annotation is two attributes on the same Rust item, a doc-comment anchor and a rustdoc
alias:

```rust
/// Replaces `fn::git_repository_open`
#[doc(alias = "git_repository_open")]
pub fn open(path: &Path) -> Result<RepositoryBox, Error> { … }
```

| anchor | meaning |
|---|---|
| ``/// Wraps `<kind>::<path>` `` | safe view over the FFI seam |
| ``/// Replaces `<kind>::<path>` `` | native Rust translation |

The anchor's path is a code span, in backticks, as rustdoc renders it and as the
workspace's `clippy::doc_markdown` lint requires of a path in a doc comment.

`<path>` names the C item, as below, and `<kind>` says what it is:

| kind | item |
|---|---|
| `fn` | a function |
| `st` | a struct |
| `un` | a union |
| `enm` | an enum, or one of its constants |
| `fnp` | a function pointer |
| `tdf` | a typedef |
| `fld` | a member of a struct or union |
| `glb` | a global |
| `mac` | a macro |

A path is made of names only: the names the source resolves the item by, outermost first,
separated by `.`, as the source language scopes them. A function, a type, an enum's
constant, a global, a typedef or a function pointer a typedef declares is its own name,
since C scopes a constant as it does its enum. A member is its struct's or union's path
followed by the member's name, and a member of a member continues the path, as
`fld::AVOption.default_val.i64`. A function pointer written inline is its declaring site's
path: a member's, `<function>.<param>` for a parameter, `<function>.return` for a return,
or a global's name. An element without a name adds no step to the paths of what it holds:

- an anonymous struct or union held by a named member is reached through that member, so
  its members are `fld::<path>.<member>.<inner>`;
- the members of an unnamed struct or union member, such as C11's anonymous members, are
  named as members of the type that holds it, as the source reaches them; and
- an array's elements are reached without an index, so the members of an array member's
  element type are `fld::<path>.<member>.<inner>`.

An element without a name has no annotation of its own. The Rust item that stands in for
it is annotated with the named member that holds it, or, when it is held by no name, with
each member it stands in for. A type declared inside another is named as its language
scopes it: a C struct tag has file scope, so a struct declared inside another is still
`st::<tag>`. An enum without a name has no annotation of its own, and its constants keep
theirs.

The alias is the bare `<path>`, without the backticks, so that a consumer who searches the
documentation for the source's name finds every item that stands in for it. The kind is
the anchor's alone: a label in the alias would no longer match that search. An item whose
own name is that path, a name of the source the Rust keeps, carries no alias: rustdoc
rejects an alias equal to its item's name, and the name already answers the search. Its
anchor is unchanged.

## 1. What is annotated

The annotation goes on the public item a consumer uses in place of the C item, which is
not necessarily the item that makes the FFI call:

- a function: the function or method the public API exports, which a consumer imports
  instead of the FFI function. The private helper that makes the call, an export
  gateway and a test are not annotated.
- a lifecycle routine, such as a C type's free function: the method of the public lifecycle
  trait that stands in for it, such as `CDrop::c_drop`, where it is handwritten, or the
  macro invocation that mints it, which passes the annotation to the method. Again, the
  method annotated need not be the one making the unsafe call.
- a type: the layout newtype that defines the FFI type, handwritten or minted by
  `define_ctype!`.
- a union: the tagged enum that stands in for it at every use.
- an enum: the Rust enum or newtype that stands in for it, and each of its constants: the
  variant or the constant that stands in for it.
- a macro: the generic, `const`, function or `macro_rules!` that stands in for it; a type
  generator's instances keep their own kinds, on the aliases.
- a function pointer: the callable type that stands in for it, or the trait, for a struct
  of function pointers.
- a typedef: the alias that stands in for it.
- a member: each of its accessors, the getter and the setter alike.

## 2. Several stand-ins

One C item may have several annotated Rust items, each carrying the same anchor and
alias: the ownership variants one C function is split into when one signature cannot
express every valid contract, and the accessors of one field. That is the only case in
which an annotation is duplicated. When an item the port first wrapped is ported, or a
wrapped struct or union takes a native layout, its `Wraps` anchor becomes a `Replaces` one,
and its alias stays.
