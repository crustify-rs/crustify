---
name: conventions
description: "Crustify's conventions: where its own files go under .crustify/, the anchors that tie each Rust item to the C item it stands in for, the lints the workspace enables, the language its texts are written in, and the git identity its commits carry. Read before placing the port's files, scaffolding the workspace, writing a public item that stands in for a C item, writing documentation, safety comments, findings, briefs or the report, or making the first commit."
---

# Conventions

## 1. Layout

Crustify keeps its own files under `.crustify/`, at the root of the repository that it
works on. Its own files are all the files that are neither the C code nor the Rust code.
In a port or a wrap, the repository is the C codebase. In an audit, it is the crate.

```text
.crustify/
├── STATUS.md                       a port or a wrap: progress per C file in scope, and the totals of time, tokens and cost
├── FITNESS.md                      a port or a wrap: the fitness brief, and each alternative's metrics
├── REPORT.md                       a port or a wrap: the final report
├── rsi/                            what the port learns that holds for this codebase alone
│   └── <id>/                       one dir per requirement
│       ├── <pattern>.md            one pattern: what it is, why, its findings, its check, its attempts
│       └── <pattern>/              its synthetic cases
├── reviews/
│   ├── REPORT-<date>.md            an audit: its final report, one per audit
│   └── <id>/                       one dir per requirement: interop, compat, api, equiv, ub, tests, ergo, …
│       └── <slug>/                 one finding, with its reproducer or witness and, under `disclose`, its draft
└── tmp/                            scratch, gitignored
```

Findings are grouped by the identifier of the requirement that they do not meet. The
reason is that the author of the next component can then read, in one place, every defect
of one kind that was found so far. The system prompt describes what a finding's directory
contains.

Rules for scratch files:

- Put every residual file under `.crustify/tmp/`: downloads, scratch builds, experiments,
  and intermediate outputs. Git ignores this directory.
- Do not put residual files anywhere else in the repository.
- A subagent uses its own subdirectory, `.crustify/tmp/<agent>/`.
- A subagent does not use a scratch directory that the host gives to every agent of a
  session, because another agent can overwrite the files there.

## 2. Anchors

Annotate the Rust item that stands in for each C item. These annotations are the only
record that an item was translated.

An annotation is two attributes on the same Rust item:

- a doc-comment anchor;
- a rustdoc alias.

After the anchor's line, add one line that names the C source file that defines the item.
Write the file's path relative to the root of the repository.

```rust
/// Replaces `fn::git_repository_open`
/// in `src/libgit2/repository.c`
#[doc(alias = "git_repository_open")]
pub fn open(path: &Path) -> Result<RepositoryBox, Error> { … }
```

| anchor | meaning |
|---|---|
| ``/// Wraps `<kind>::<path>` `` | safe view over the FFI seam |
| ``/// Replaces `<kind>::<path>` `` | native Rust translation |

Format rules:

- Write the anchor's path and the source file as code spans, in backticks. Rustdoc renders
  them this way, and the workspace's `clippy::doc_markdown` lint requires it for a path in
  a doc comment.
- Keep the anchor alone on its line, so that ffimap can read it. Rustdoc joins the two
  lines into one sentence.

In an anchor, `<path>` names the C item and `<kind>` says what the item is:

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

A path contains names only. Use the names that the source code uses to resolve the item,
starting with the outermost name, and separate them with `.`. For example,
`fld::AVOption.default_val.i64` names a member of a member.

One C item can have several annotated Rust items. In that case, repeat the annotation:
each Rust item carries the same anchor and the same alias.

## 3. Lints

The workspace enables the following lints, and denies warnings:

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

Programmers and agents read the texts that Crustify writes, so write them plainly. Follow
the [Google developer documentation style guide](https://developers.google.com/style):

- Use one term for each thing.
- Write short sentences.
- Put a condition before its consequence.
- Use a list for parallel items.

Two more rules:

- Keep the reason for each rule, because agents generalize from reasons.
- When you rewrite a text, keep every fact of the old text. The review of the rewrite
  checks this.

## 5. Identity

Unless the user says otherwise, author and commit every commit as Crustify:
`crustify <crustify@berkeley.edu>`. The GitHub account of this identity is `crustify-ai`.
Add a `Co-Authored-By:` trailer only for a co-author that the user names.
