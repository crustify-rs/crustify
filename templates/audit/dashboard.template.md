# Crustify audit — `<target repo>`

Copy this template into the audited checkout, then fill it as work lands. All
prose belongs in Notes.

## Run

- **target repo** — `<repo>` @ `<commit>`
- **crate** — `<name>` `<version>`
- **objectives** — `<any of: audit, revisit, fix>`
- **reviewer objectives** — `<ub, equiv, disclose, fix, ...>`
- **agent backend** — `<claude | codex>`
- **model** — `<provider>/<model>`
- **billing** — `<api | subscription>`
- **maximum spend** — `$<n>`; reached: `<yes | no>`
- **instruments** — `<miri | asan/ubsan | bsan | msan | tsan | equivalence | combination>`
- **deps** — crustify `<sha>` (`<branch>`)

## Findings

One row per CONFIRMED finding: a sanitizer reported UB, or an equivalence
assertion failed, on a reproducer that links the real crate.

| finding | site | review batch | instrument | reported | fixed | patch |
|---|---|---|:-:|:-:|:-:|---|
| `<kind>/<slug>` | `<file>:<line>` | `<batch id>` | `miri` | ✓ | | `<commit>` |
| `<kind>/<slug>` | `<file>:<line>` | `<batch id>` | `asan/ubsan` | | | |
| **Σ `<n>` findings** | | | **one count per SELECTED instrument, e.g. `miri` `<n>` · `asan/ubsan` `<n>` · `bsan` `<n>` · `msan` `<n>` · `tsan` `<n>` · `equivalence` `<n>`** | **`<n>`** | **`<n>`** | **`<n>` fixed** |

## Revisited

Only for a `revisit` objective.

- **still reproduce** — `<n>`
- **no longer reproduce** — `<n>`, with the commit that changed each verdict
- **removed** — `<n>`, never a defect

## Scope

Modules the reviewers were given. The per-batch split is in the table below.

```
<path>
<path>
```

- **files reviewed** — `<n>` of `<n>` in the crate
- **not reviewed** — `<dirs / globs, and why>`

## Review batches

One row per reviewer. `wall` is `ended_at − started_at` from its
`reviewer.usage.json`, so it includes whatever it spent building the C library.
`$` is that record's `cost_usd`, from `crustify usage`; under subscription billing it is an
API-equivalent comparison value, not a charged amount.

| batch | workset | files | wall | $ | findings |
|---|---|---:|---|---:|---:|
| `<batch id>` | `<modules / reports>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>` |
| `<batch id>` | `<modules / reports>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>` |
| assistant | — | — | — | `$<n>`+ | — |
| **Σ `<n>` agents** | | **`<n>`** | **`<n>`h`<n>`m** | **`$<n>`** | **`<n>`** |

## Legend

- **finding** — its dir under the filing batch's reviews dir,
  `crustify/reviews/<batch id>/`
- **instrument** — the selected instrument that fired on this finding. One tag
  per row: a finding exists because something crashed or an assertion failed,
  and this names what caught it. A tag missing from the whole column is not a
  clean bill — record in Notes what each instrument was and was not run
  against. Miri cannot reach a faulting access inside C; bsan is the one that
  answers aliasing across that seam; msan is the one that sees uninitialized
  memory, which asan/ubsan does not model at all; tsan is the only one that
  answers a hand-written `Send`/`Sync`
- **reported** — `✓` once the finding has been sent to its recipient, per its
  `disclosure.md`; blank means drafted but not yet sent
- **fixed** — `✓` once a fix has landed upstream or in the audited project;
  blank if not tracked
- **site** — where the bug is, not where the reproducer is
- **patch** — the commit carrying the reviewer's fix; blank without `fix`
- **files** — size of that batch's modules; blank for a revisit batch

## Notes

`<what the numbers do not say>`
