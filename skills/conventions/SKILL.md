---
name: conventions
description: "The port's conventions: where its own files go under .crustify/, the anchors that tie each Rust item to the C item it stands in for, the lints the workspace enables, and the language its texts are written in. Read before placing the port's files, scaffolding the workspace, writing a public item that stands in for a C item, or writing documentation, safety comments, findings, briefs or the report."
---

# Conventions

## 1. Layout

The port's own files, everything that is neither the C nor the Rust, sit under
`.crustify/` at the root of the C codebase's repository:

```text
.crustify/
├── STATUS.md                       progress per C file in scope, and the totals of time, tokens and cost
├── REPORT.md                       the final report
├── reviews/
│   └── <id>/                       one dir per requirement: interop, compat, api, equiv, ub, perf, …
│       └── <slug>/                 one finding
└── tmp/                            scratch, gitignored
```

Findings are grouped by the identifier of the requirement they fall short of, so that the
author of the next component reads every defect of a kind found so far in one place. What
a finding's directory holds is the system prompt's Review section's.

`.crustify/tmp/` is gitignored and holds anything residual: downloads, scratch builds and
experiments, intermediate outputs. Residual files go nowhere else in the repository. A
subagent's scratch is its own subdirectory, `.crustify/tmp/<agent>/`, never a directory the
host hands every agent of a session, where another agent can overwrite it.

## 2. Anchors

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

One C item may have several annotated Rust items, each carrying the same anchor and
alias, in which case an annotation is duplicated.

## 3. Lints

The workspace enables these lints, with warnings denied:

- rustc:
  - `nonstandard_style`
  - `unsafe_code`
  - `unsafe_op_in_unsafe_fn`
  - `missing_docs`
  - `rust_2018_idioms`
  - `unreachable_pub`
  - `unused_qualifications`
  - `unused_lifetimes`
  - `let_underscore_drop`
  - `trivial_casts`
  - `trivial_numeric_casts`
- Clippy:
  - `clippy::correctness`
  - `clippy::all`
  - `clippy::pedantic`
  - `clippy::cargo`
  - `clippy::undocumented_unsafe_blocks`
  - `clippy::multiple_unsafe_ops_per_block`
  - `clippy::missing_safety_doc`
  - `clippy::unnecessary_safety_comment`
  - `clippy::unnecessary_safety_doc`
  - `clippy::mem_forget`
  - `clippy::allow_attributes`
  - `clippy::allow_attributes_without_reason`

## 4. Language

Programmers and agents read a port's texts, so they are written plainly, as the
[Google developer documentation style guide](https://developers.google.com/style)
describes: one term per thing, short sentences, a condition before its consequence, lists
for parallel items. A rule keeps its reason, since agents generalize from reasons. A
rewrite keeps every fact of the old text, which its review checks.
