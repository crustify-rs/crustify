---
name: conventions
description: "Crustify's conventions: where its own files go under .crustify/, the anchors that tie each Rust item to the C item it stands in for, the lints the workspace enables, the language its texts are written in, the git identity its commits carry, and the format of an audit's disclosure drafts. Read before placing the port's files, scaffolding the workspace, writing a public item that stands in for a C item, writing documentation, safety comments, findings, briefs or the report, making the first commit, or writing a disclosure draft."
---

# Conventions

## 1. Layout

Crustify's own files, everything that is neither the C nor the Rust, sit under
`.crustify/` at the root of the repository it works on: the C codebase's, or in an audit
the crate's:

```text
.crustify/
├── STATUS.md                       progress per C file in scope, and the totals of time, tokens and cost
├── FITNESS.md                      the fitness brief, and the Pareto frontier's points
├── REPORT.md                       the final report
├── rsi/                            what the port learns that holds for this codebase alone
│   └── <id>/                       one dir per requirement
│       ├── <pattern>.md            one pattern: what it is, why, its findings, its check, its attempts
│       └── <pattern>/              its synthetic cases
├── reviews/
│   ├── notes.md                    in an audit: nits, and what could not be reproduced
│   └── <id>/                       one dir per requirement: interop, compat, api, equiv, ub, tests, ergo, …
│       └── <slug>/                 one finding, with its reproducer and, under `disclose`, its draft
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
alias. The anchor's line is followed by one naming the C source file that defines the
item, relative to the repository's root:

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

The anchor's path and the source file are code spans, in backticks, as rustdoc renders
them and as the workspace's `clippy::doc_markdown` lint requires of a path in a doc
comment. The anchor stays alone on its line, so that ffimap reads it; rustdoc joins the
two lines into one sentence.

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

## 5. Identity

Every commit is authored and committed as Crustify, `crustify <crustify@berkeley.edu>`,
whose GitHub account is `crustify-ai`, whatever the repository's git configuration says,
unless the user names another author. The message carries a `Co-Authored-By:` trailer only
for a co-author the user names, and no other, none the host suggests included. Pass the
identity on the command line, `git -c user.name=crustify -c user.email=crustify@berkeley.edu
…`, to every command that writes a commit, a merge, a rebase or a cherry-pick as much as a
commit, since the host may have no git identity of its own.

## 6. Disclosures

Under an audit's `disclose` mode, `disclosure.md` opens with a header, then a `---` line,
then the body that the user sends:

- `status`: `to file`; `do not file: <reason>`; `reported: <url>`, the upstream issue; or
  `fixed: <url>`, the change that fixed it. It is the one record of the disclosure's fate:
  keep it current as the user tells you what they sent.
- `channel`: where the project asks for such reports, from its `SECURITY.md`, its issue
  templates and its contributing guide: a private advisory or an email, with the
  maintainers named, or a public issue. Flag a project that refuses machine-written text:
  its draft is then notes for the user to rewrite, not text to paste.
- `upstream`: the revisions the reproducer was rerun on, the latest release and the tip of
  the default branch, and whether each shows the defect.

A defect already reported or fixed upstream gets the header alone, with the issue or the
fix as its status. The body is written for the project's maintainers: what goes wrong and
where, the reproducer and its output, the versions affected, and a fix where one is clear.
