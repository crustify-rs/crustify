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
separated by `.`, as `fld::AVOption.default_val.i64` names a member of a member.

## 2. Several stand-ins

One C item may have several annotated Rust items, each carrying the same anchor and
alias, in which case an annotation is duplicated.
