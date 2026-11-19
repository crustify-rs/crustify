---
name: reviewing-reports
description: "How review findings are filed: one directory per finding under its kind, its class, evidence, conditions and root cause, notes, and reproducers. Read before filing or revisiting a finding."
---

# Reviewing: reports

What a review files for what [`reviewing`](../SKILL.md)'s kinds of finding name: a
file per finding, one finding per root cause, and the reproducer that proves each.

## 1. Findings

A finding is a directory under its kind, the objective that names it,
`.crustify/reviews/<kind>/<slug>/`, as [`layout`](../../../operations/layout/SKILL.md)
places it. The slug names the defect in a few words, such as `index-entry-alias`. The
directory holds `finding.md`, the finding itself, and its reproducer, when it has one. Its
id, `<kind>/<slug>`, such as `ub/index-entry-alias`, stays its name in every later review
and commit that refers to it. A finding is never deleted once filed: a later review updates
`finding.md` in place, its status and the verdict of each rerun.

A defect in a tool rather than in the port, ffibox or ffimap included, is no finding of
the component: it is filed as a finding of the kind `tools`, with its reproducer, for the
agent to fix in the tool.

A finding states what is wrong, where, the evidence that proves it, and, once fixed, how
it was fixed and in which commit. It names the check that caught it, such as the author's
tests, a review, a later review or the remaining C's tests, and
the checks that had the same code in scope before it and missed it: a finding an earlier
check missed is an escape. It carries
everything needed to rerun its reproducer from a clean checkout: the exact command and the
sanitizer output or failing assertion it produced. Neither a finding nor a reproducer
carries an API key, in a core dump or anywhere else.

### 1.1 Header

A finding opens with its title, then its header, one `key: value` line each:

- `component`: the component it was found in, and every other it reaches;
- `reviewed`: the commit the review that filed it reviewed;
- `class`, as [Classes](#12-classes) gives it;
- `evidence`: what decided it, a sanitizer, Miri or a failing assertion, by name. A
  result that only an aliasing model reports, Stacked Borrows, Tree Borrows or BSan, adds
  `aliasing-model only`; one that rests on a claim the Rust Reference does not settle,
  such as a reference to an uninhabited opaque type or to a partly initialised struct,
  adds `unsettled`. Either says so wherever the finding states the defect, and neither is
  called undefined behaviour without that qualifier;
- `conditions`: the Cargo features, target and `cfg`s it needs, whether it needs a system
  C library rather than the bundled one, or a version of it, and the revisions it
  reproduces on;
- `status`: `open`, `fixed <commit>`, or `left: <reason>`; and
- `same-cause`, where another finding has the same root cause: that finding's id.

### 1.2 Classes

| class | what the finding shows |
|---|---|
| `soundness` | undefined behaviour reached from the safe public API, from the unsafe public API within its `# Safety` obligations, or by C through an export within the C declaration's contract |
| `c-bug` | a defect of the C library itself, which its own API reaches without the port's doing |
| `behaviour` | no undefined behaviour: a panic, a wrong value, a swallowed error, a leak, a slowdown, or a divergence from the C or the specification |
| `nit` | nothing a consumer can observe: a missing or imprecise `// SAFETY:` justification, an under-documented `# Safety` obligation that no reproducer breaks, or an API-shape finding of `unsafety`, `interop`, `ergonomics`, `idiom` or `anchors` |

What only misuse can reach is not reportable: a private item no public API reaches with
the inputs in question, or an `unsafe` API called against its stated obligations.

### 1.3 Root causes

A finding is one root cause. Sites that share a defect are one finding that lists them,
whatever objective or instrument met each. Before a finding is filed, the findings already
in `.crustify/reviews/` are searched for its cause, by site and mechanism, not by name: one
the same review filed takes the new site; one an earlier review filed is named in
`same-cause`, so that a class of defect that recurs across components shows as one. A
finding that several objectives meet is filed once, under the kind that names its harm.

### 1.4 Notes

A candidate that reading supports and no true reproducer can show is a note, marked
`unproven`, with why none is possible. A `nit` may be a note too: one line with its site.
A kind's notes sit in one file, `.crustify/reviews/<kind>/notes.md`, each naming its
component.

## 2. Reproducers

A `ub`, `equiv` or `functional` candidate becomes a finding only once a reproducer proves it,
and so does a `contracts` candidate that claims a contract can be broken, and a `perf`
candidate, whose reproducer is the measurement. A contract that merely asks for more than
the implementation needs, or a missing justification, is a finding without one.

- A UB reproducer triggers one of the available sanitizers, or Miri, from Rust, and its
  finding carries the trace. One targeting the safe public API carries
  `#![forbid(unsafe_code)]`; one targeting the unsafe API, or breaking a contract, honours
  the `# Safety` obligation, and its finding says, for each `unsafe` it writes, why the
  defect is still the port's. One reaching an export calls it as C would, through its raw
  binding, or from a C program, within the C declaration's contract.
- An equivalence reproducer fails a comparison of the C and the Rust, as
  [`testing`](../../testing/SKILL.md) lists them, while running the raw C and the public Rust API, and its finding carries the
  failing assertion. Once the C is gone, a behaviour finding is a `functional` one.
- A functional reproducer fails a Rust assertion of what the specification it cites requires,
  and its finding carries the failing assertion.

Each reproducer is a standalone Cargo package: its `Cargo.toml` declares an empty
`[workspace]` table and depends on the affected crate through a relative `path`, and its
`src/main.rs` runs one scenario, so that running it exits non-zero on the affected commit.
A reproducer that must run as C does is a C program built against the port's headers and
library, with its build command in the finding.

Whatever its kind, a reproducer is a true proof of concept:

- it links the affected crate itself and reaches the defect through its public API or its
  exports: it copies none of the crate's code, a private module included, and stands in
  for no part of the crate or of the C with a stub or a model;
- it is deterministic: every run gives the same verdict, and one that depends on an
  interleaving runs under the sanitizer that reports the race whichever thread wins;
- it fails visibly, for the reason its finding states, and would pass were the defect
  absent: a comparison that passes, or a failure of the reproducer's own setup, proves
  nothing; and
- it is minimal: one scenario, with nothing the failure does not need.
