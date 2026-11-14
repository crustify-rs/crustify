---
name: reviewing-reports
description: "How a review's findings are filed: report directories, classes, evidence, conditions, root causes, notes, reproducers, and disclosure drafts with their upstream check and status. Read before filing or revisiting a finding, drafting or checking a disclosure, or consolidating a campaign's reports."
---

# Reviewing: reports

What a review files for the defects [`reviewing`](../SKILL.md)'s objectives name: a report
per root cause, the reproducer that proves it, and, under `disclose`, the draft its
project's maintainers are sent.

## 1. Reports

A review batch files its findings under its reviews dir, as
[`layout`](../../../operations/layout/SKILL.md)'s Reviews section spells it,
each in its own `<slug>` directory, holding its report and, when it has one, its
reproducer, in the sub-directory of its objective:

| objective | sub-directory |
|---|---|
| `unsafety` | `unsafe/` |
| `contracts`, of a gateway | `contracts/ffi_export/` |
| `contracts`, of other unsafe code | `contracts/ffi_import/` |
| `ub`, on the safe interface | `ub_safe/` |
| `ub`, on the unsafe interface | `ub_unsafe/` |
| `ub`, through an export | `ub_export/` |
| `equiv` | `equiv/` |
| `logic` | `logic/` |
| `ergonomics` | `ergonomics/` |
| `idiom` | `idiom/` |
| `conventions` | `conventions/` |
| `misc` | `misc/` |

A tool may add sub-directories for findings on its own output. A defect in a tool
rather than in the reviewed codebase, Crustify included, is no finding: it is a proposal,
with its reproducer, as [`evolution`](../../../crustify/evolution/SKILL.md)'s Proposals
section describes.

A report states what is wrong, where, the evidence that proves it, and, under `fix`, how it
was fixed. It names the tier that caught the finding, and the tiers that had the same code
in scope before it and passed it. The tiers are a batch's own gates, a review batch, a
module pass, a switch, a later stage's review, a revisit, a ship point's gates and a
consumer. A finding caught by a later tier than the first that had it in scope is an
escape. A finding of `ub` or `contracts` also names the pattern of
[`soundness`](../../../rust/soundness/SKILL.md) it is an instance of, or `new`. A finding that a switch, a ship point's gates or a consumer catches is filed by the
review batch it is handed to, which names that tier. It carries everything needed to rerun
its reproducer from a clean checkout: the exact command and the sanitizer output or failing
assertion it produced. Neither a report nor a reproducer carries an API key, in a core dump
or anywhere else: a reviews dir may be published.

### 1.1 Header

A report opens with its header, one `key: value` line each:

- `class`, as [Classes](#12-classes) gives it;
- `evidence`: what decided it, a sanitizer, Miri or a failing assertion, by name. A
  result that only an aliasing model reports, Stacked Borrows, Tree Borrows or BSan, adds
  `aliasing-model only`; one that rests on a claim the Rust Reference does not settle,
  such as a reference to an uninhabited opaque type or to a partly initialised struct,
  adds `unsettled`. Either says so wherever the report or its disclosure states the
  defect, and neither is called undefined behaviour without that qualifier;
- `conditions`: the Cargo features, target and `cfg`s it needs, whether it needs a system
  C library rather than the bundled one, or a version of it, and the revisions it
  reproduces on; and
- `same-cause`, where another report in the tree has the same root cause: that report's
  dir.

### 1.2 Classes

| class | what the report shows |
|---|---|
| `soundness` | undefined behaviour reached from the safe public API, from the unsafe public API within its `# Safety` obligations, or by C through an export within the C declaration's contract |
| `c-bug` | a defect of the C library itself, which its own API reaches without the crate's doing |
| `behaviour` | no undefined behaviour: a panic, a wrong value, a swallowed error, a leak, or a divergence from the C or the specification |
| `nit` | nothing a consumer can observe: a missing or imprecise `// SAFETY:` justification, an under-documented `# Safety` obligation that no reproducer breaks, or an API-shape finding of `unsafety`, `ergonomics`, `idiom` or `conventions` |

What only misuse can reach is not reportable and gets no report: a private item no public
API reaches with the inputs in question, or an `unsafe` API called against its stated
obligations.

### 1.3 Root causes

A report is one root cause. Sites that share a defect are one report that lists them,
whatever objective or instrument met each. Before a finding is filed, the reports already
in the tree are searched for its cause, by site and mechanism, not by name: one a batch
of its own filed takes the new site; one another batch filed is named in `same-cause`.

### 1.4 Notes

Outside a Crustify-generated crate, a `nit` gets no report directory: it is one line, with
its site, in the batch's `notes.md` at the root of its reviews dir, grouped by kind, such
as unjustified `unsafe` blocks. So is a candidate that reading supports and no true
reproducer can show, as `unproven`, with why none is possible. A campaign keeps one such
note per crate, merged from its batches'.

## 2. Reproducers

A `ub`, `equiv` or `logic` candidate becomes a finding only once a reproducer proves it,
and so does a `contracts` candidate that claims a contract can be broken. A contract that
merely asks for more than the implementation needs, or a missing justification, is a
finding without one.

- A UB reproducer triggers one of the available sanitizers from Rust, and its report
  carries the sanitizer's trace. One targeting the safe public API carries
  `#![forbid(unsafe_code)]`; one targeting the unsafe API, or breaking a contract, honours
  the `# Safety` obligation, and its report says, for each `unsafe` it writes, why the
  defect is still the crate's. One reaching an export calls it as C would, through its
  raw binding, within the C declaration's contract.
- An equivalence reproducer fails one of [`testing`](../../testing/SKILL.md)'s equivalence
  comparisons while running the raw C and the public Rust API, and its report carries the
  failing assertion. Once the C is gone, a behaviour finding is a `logic` one.
- A logic reproducer fails a Rust assertion of what the specification it cites requires,
  and its report carries the failing assertion.

Each reproducer is a standalone Cargo package: its `Cargo.toml` declares an empty
`[workspace]` table and depends on the affected crate through a relative `path`, and its
`src/main.rs` runs one scenario, so that running it exits non-zero on the affected commit.

Whatever its kind, a reproducer is a true proof of concept:

- it links the affected crate itself and reaches the defect through its public API: it
  copies none of the crate's code, a private module included, and stands in for no part
  of the crate or of the C with a stub or a model;
- it is deterministic: every run gives the same verdict, and one that depends on an
  interleaving runs under the sanitizer that reports the race whichever thread wins;
- it fails visibly, for the reason its report states, and would pass were the defect
  absent: a comparison that passes, or a failure of the reproducer's own setup, proves
  nothing; and
- it is minimal: one scenario, with nothing the failure does not need.

## 3. Disclosure

Under `disclose`, a report of class `soundness`, `c-bug` or `behaviour` gets a
`disclosure.md` beside it, a `c-bug`'s addressed to the C library's project. It is a draft
for the user to send: a review opens no issue, pull request or advisory, and sends and
posts nothing.

### 3.1 Upstream check

Before a draft is written, the project is checked upstream, unless the campaign's
settings turn the check off: its tracker's open and closed issues and pull requests are
searched for the defect, and the reproducer is rerun on the latest release and on the tip
of the default branch, not only on the reviewed revision. A query to an outside service
carries only generic technical terms, an API's name or an error's text, never the
report, the reproducer or anything of the campaign or its user. A defect already reported
or already fixed gets no draft beyond its header, with the issue or the fix as its
status, and its report's `conditions` say which of the revisions are affected. Without
the check, the header says `upstream: unchecked`.

### 3.2 Draft

`disclosure.md` opens with a header, then a `---` line, then the body the user sends:

- `status`: `to file`; `DO NOT FILE: <reason>`; `REPORTED: <url>`, the upstream issue; or
  `FIXED: <url>`, the pull request or commit that fixed it. It is the one record of the
  disclosure's fate, kept current as the user reports what they sent;
- `channel`: where the project asks for such reports, from its `SECURITY.md`, its issue
  templates and its contributing guide at the default branch: a private advisory or an
  email, with the maintainers named, or a public issue. A project that refuses
  machine-written text is flagged here, and its draft is notes for the user to rewrite,
  not text to paste; and
- `title`: a plain line naming the API and the effect, which the body does not repeat as
  a heading.

The body follows the project's conventions and holds, in 150 to 250 words of prose:

- two to four sentences on what goes wrong, and under which of the report's `conditions`;
- the minimal reproducer inline, and a few lines of its real output;
- the exact versions it was run on, the crate's, the C library's and the toolchain's; and
- one or two sentences on a possible fix.

Every statement in it is one the review verified by running or reading: no history, no
counts, no comparison with other projects and no speculation about exploitability. It
uses none of the campaign's vocabulary, such as a wave, a batch or an objective. It ends
with: `Found by [Crustify](https://github.com/crustify-rs/crustify), an experimental
UB/soundness auditing agent developed at UC Berkeley and running on <model name>, then
manually reviewed and independently reproduced.`

A possible fix may be tried on a copy of the tree in the batch's scratch, without `fix`:
the draft calls it tested only when the reproducer stops failing and the crate's own
tests pass with it. A patch is offered only under `fix`.
