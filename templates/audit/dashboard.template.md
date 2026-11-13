# Crustify audit — `<target repo>`

Copy this template into the audited checkout, then fill it as work lands. All
prose belongs in Notes.

## Run

- **target repo** — `<repo>` @ `<commit>`; since `<earlier commit | none>`
- **crate** — `<name>` `<version>`; latest release `<version>`; default branch `<commit>`
- **tasks** — `<any of: audit, revisit, fix>`
- **review objectives** — `<all: ub, contracts, equiv, logic, ... | the objectives named>`
- **crate pass** — `<yes | no>`; run: `<yes | no, why>`
- **agent** — `<claude | codex>`, proxy `<proxy | none>`, args `<args | none>`; model `<model>`
- **billing** — `<api | subscription>`
- **instruments** — `<miri | asan/ubsan | bsan | msan | tsan | equivalence | combination>`; unavailable, so untested: `<instruments | none>`
- **tool hints** — `<yes | no>`; `<tool>` `<ran | absent | partial | failed>`
- **disclosure** — `<drafts | none>`; upstream check `<yes | no>`
- **deps** — crustify `<sha>` (`<branch>`)

## Budget

- **maximum spend** — `$<n>`
- **spent** — `$<n>`: reviewers `$<n>`, assistant `$<n>`, evolution reviews `$<n>`
- **guard** — `<not reached | stopped the audit at $<n>>`; reviewers stopped: `<batch ids | none>`
- **left unreviewed for the budget** — `<worksets, in priority order | none>`

## Findings

One row per root cause, once consolidated: a report of class `soundness`, `c-bug` or
`behaviour`, proved by a reproducer that links the real crate through its public API.

| finding | class | site | review batch | evidence | affects | status | reported | fixed | patch |
|---|---|---|---|---|---|---|---|---|---|
| `<kind>/<slug>` | `soundness` | `<file>:<line>` | `<batch id>` | `miri` | `<release and default branch>`, feature `<f>` | `REPORTED` | [#`<n>`](`<issue url>`) | [#`<n>`](`<pr url>`) | `<commit>` |
| `<kind>/<slug>` | `behaviour` | `<file>:<line>` | `<batch id>` | `assertion` | `<default branch only>`, system `<lib>` | `to file` | | | |
| `<kind>/<slug>` | `soundness` | `<file>:<line>` | `<batch id>` | `bsan`, aliasing-model only | `<…>` | `DO NOT FILE: <reason>` | | | |
| **Σ `<n>` findings** | **`soundness` `<n>` · `c-bug` `<n>` · `behaviour` `<n>`** | | | **one count per SELECTED instrument, e.g. `miri` `<n>` · `asan/ubsan` `<n>` · `equivalence` `<n>`; `aliasing-model only` `<n>` · `unsettled` `<n>`** | | **`to file` `<n>` · `DO NOT FILE` `<n>`** | **`<n>`** | **`<n>`** | **`<n>` fixed** |

- **merged as duplicates** — `<n>` reports into `<n>` findings
- **notes** — [`crustify/reviews/notes.md`](../reviews/notes.md): `<n>` nits, `<n>` unproven

## Revisited

Only for a `revisit` task.

- **still reproduce** — `<n>`
- **no longer reproduce** — `<n>`, with the commit that changed each verdict
- **removed** — `<n>`, never a defect

## Scope

The worksets, in priority order, each with the reading its priority rests on. The
per-batch split is in the table below.

| priority | workset | why here | batch |
|---:|---|---|---|
| `<n>` | `<paths / commits>` | `<what the source shows: safe API reaching C with consumer-held lifetimes, a hand-written Sync, …>` | `<batch id \| not reached>` |

- **files reviewed** — `<n>` of `<n>` in the crate
- **not reviewed** — `<dirs / globs, and why: no variant compiles them, the budget, …>`

## Review batches

One row per reviewer. `wall` is `ended_at − started_at` from `crustify-usage` on its
transcript, so it includes whatever it spent building the C library. `$` is that usage's
`cost_usd`; under subscription billing it is an API-equivalent comparison value, not a
charged amount.

| batch | workset | objectives | files | wall | $ | reports | notes |
|---|---|---|---:|---|---:|---:|---:|
| `<batch id>` | `<paths / commits / reports>` | `<objectives>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>` | `<n>` |
| `<batch id>` | crate pass | `<objectives>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>` | `<n>` |
| assistant | — | — | — | — | `$<n>` | — | — |
| **Σ `<n>` agents** | | | **`<n>`** | **`<n>`h`<n>`m** | **`$<n>`** | **`<n>`** | **`<n>`** |

## Legend

- **finding** — its dir under the filing batch's reviews dir,
  `crustify/reviews/waves/<batch id>/`
- **class** — the report's `class`: `soundness`, `c-bug` or `behaviour`; a `nit` has
  no row, only a line in the notes
- **evidence** — what proved the finding: the selected instrument that fired, or
  `assertion`; with `aliasing-model only` or `unsettled` where the report's header
  carries it. A tag missing from the whole column is not a clean bill — record in
  Notes what each instrument was and was not run against. Miri cannot reach a
  faulting access inside C; bsan is the one that answers aliasing across that seam;
  msan is the one that sees uninitialized memory, which asan/ubsan does not model
  at all; tsan is the only one that answers a hand-written `Send`/`Sync`
- **affects** — the report's `conditions`: the latest release, the default branch
  or both; the Cargo feature; a system C library where the bundled one is unaffected
- **status** — the `status` of the finding's `disclosure.md`: `to file`,
  `DO NOT FILE: <reason>`, `REPORTED` or `FIXED`; `—` without a draft
- **reported** — the upstream issue, linked, once the status is `REPORTED` or `FIXED`
- **fixed** — the upstream pull request or commit that fixed it, linked, once the
  status is `FIXED`
- **site** — where the bug is, not where the reproducer is
- **patch** — the commit carrying the reviewer's fix; blank without `fix`
- **reports** / **notes** — what a batch filed, before consolidation: report dirs, and
  lines of its `notes.md`
- **files** — size of that batch's modules; blank for a revisit batch

## Notes

`<what the numbers do not say>`
