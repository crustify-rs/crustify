# crustify — `<target repo> / <target>`

Copy this template into the campaign checkout, then fill it as work lands.

## Campaign

- **target repo** — `<repo>` @ `<commit>`
- **target** — `<target>`
- **campaign objective** — `<port | wrap>`
- **`impl_files`** — `<dirs / files>`
- **`api_headers`** — `<dirs / files>`
- **agent backend** — `<codex | claude>`
- **model** — `<provider>/<model>`
- **`--billing`** — `<api | subscription>`
- **`--max-types`** — `<n>`
- **`--max-syms`** — `<n>`
- **`--max-loc`** — `<n>`
- **`--min-fields`** — `<n>`
- **orchestrator parallelism** — `<n>` concurrent batch processes
- **branch** — `<branch>`, tip `<sha>`
- **deps** — crustify `<sha>` (`<branch>`), ffibox `<sha>` (`<branch>`)
- **build version** — `<build.json version>`
- **C test baseline** — `<passed>/<total>, <skipped>, and every disabled test`

## Review pass

Thin batches with `"objective": "review"`, LLM-as-a-Judge over each landed wave.

- **agent backend** — `<codex | claude>`
- **model** — `<provider>/<model>`
- **`--billing`** — `<api | subscription>`
- **`--max-types`** — `<n>`
- **`--max-syms`** — `<n>`
- **`--max-loc`** — `<n>`
- **`--min-fields`** — `<n>`
- **orchestrator parallelism** — `<n>` concurrent batch processes
- **branch** — `<branch>`, tip `<sha>`
- **agents** — `<n>`, over `<n>` wave(s)

`rv`-prefixed columns below carry the review pass; the unprefixed ones remain
the campaign's.

## UB pass

`crustify-audit ub`, an agentic hunt for undefined behaviour reachable from the
crate's SAFE APIs.

- **agent backend** — `<codex | claude>`
- **model** — `<provider>/<model>`
- **`--billing`** — `<api | subscription>`
- **`--timeout`** — `<n>` min — a wall BUDGET, not a kill switch: agents are
  spawned one after another until it is reached and each finishes on its own,
  so the run overshoots by however long the last one takes. `0` runs exactly
  one agent
- **subject** — `<sub-campaign>` at `<sha>`
- **agents** — `<n>`, `<n>h<n>m<n>s` wall, `$<n>`
- **advisories** — `<n>` at `crustify/audit/advisories/`
- **patch** — `<branch>` at `<sha>`; `<merged | left unpromoted — reason>`

`ub`-prefixed columns carry this pass.

## Legend

- `objective` — what the batch's agents were told to do: `wrap`, `port`, or
  `raw lifetime`; the Overview also carries `review` for a judged wave, `ub` for
  the UB pass, and `orchestration` for the driving agent. The type tables are
  split by it, so it appears as a column only in `Batches — symbols`, which
  mixes the two
- `wave` / `batch` — the batch's position in its sub-campaign's plan: the index
  of its wave in `waves` and of the batch within that wave's `batches`, so a
  batch row joins to `waves.json`, to the agent that landed it, and to its
  Overview sub-campaign row. Schema-v2 plans carry `steps` and `plan_items`
  rather than indexed waves and batches, so historical rows leave both blank
- `types` / `symbols` — scheduler units in the batch. Callbacks are scheduled
  in symbol batches and counted there
- `fields` — in-scope fields: the field accessors the oracle assigned to that
  type batch, not the type's full declared field count
- `lifecycle prims` — deleters, disposers and cloners the ownership store binds
  to that batch's types; raw-tier primitives that belong to no type are counted
  in `Raw lifetime discovery` instead
- `$` / `wall` / `loc` — that agent's computed cost, its elapsed time, and the
  `.rs` insertions of its landing commit. `wall` is `ended_at − started_at` from
  the agent's own `usage.json`, so it INCLUDES the per-worktree C rebuild
- `$/type` / `$/symbol` / `$/field` / `$/loc` — that row's `$` over its units,
  its in-scope fields, or its `loc`
- `$/type` / `$/sym` — in the Overview, a sub-campaign's cost over the types or
  symbols it was scheduled for; `—` where it was scheduled for none
- `+LoC` — the landed sub-campaign's Rust-source insertions/deletions relative
  to its parent campaign state
- `+UB tests` / `+equiv tests` / `+unit tests` — tests added by that landed
  sub-campaign; each parenthesized pair is its C/Rust line-coverage change in
  percentage points. Negative coverage deltas are valid when the landed source
  adds more executable lines than the new tests cover
- `rv $` / `rv wall` / `rv loc` — the REVIEW agent's cost, elapsed time, and net
  `.rs` line delta (`+ins/-del`) of its landing commit. Under subscription
  billing `rv $` is an API-equivalent comparison value, not a charged amount
- the UB pass is a row, not a pair of columns: `crustify-audit ub` schedules no
  types or symbols and lands no tests, so it fills only `wave wall` and
  `total`, and the row is omitted entirely where the optional pass did not run
- `UB tests` / `Equiv tests` / `Unit tests` — counts of `#[test]`
  functions under `mod ub_tests` / `mod equiv_tests` / `mod units_tests`. Each
  coverage pair comes from running only that workload, against the
  coverage-instrumented target C sources and authored Rust sources; state any
  excluded files or generated code in Notes. The three workloads bound different
  obligations, so report them apart and never sum them. Report the UB
  workload once, from a single coverage run on the plain build: it executes once
  per prepared sanitizer, but those runs share one test set and re-counting them
  inflates the figure. Name the instruments it ran under in Notes
- `Total tests` — the three counts added. Its coverage pair is NOT the three
  pairs added: it comes from one run of all three workloads together and is the
  union of the lines any of them reached, which is smaller than the sum wherever
  two workloads cover the same line. Deriving it arithmetically overstates it.
  It is a reach figure only — it mixes three verdict sources and so bounds no
  single obligation, which is why the three stay reported apart above it

Every table below is a heading, a model line and the table. All prose belongs
in Notes.

## Overview

- **Rust LoC, non-test** — `<n>`
- **Rust LoC, tests** — `<n>`
- **UB tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Equiv tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Unit tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Total tests** — `<sum of the three counts>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **C LoC** — `<n>`
- **ported types** — `<n>`
- **ported symbols** — `<n>`
- **wrapped types** — `<n>`
- **wrapped symbols** — `<n>`

Implementation `<provider>/<model>` via `<backend>`; review
`<provider>/<model>` via `<backend>`. Each row names the model that produced
it.

| sub-campaign | objective | nr types | nr symbols | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | wave wall | total | $/type | $/sym |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| `<waves>-<name>` | raw lifetime | `0` | `<n>` | `+<n>/-<n>` | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `<n>m<n>s` | `$<n>` (`<model>`) | — | `$<n>` |
| `<waves>-<name>` | wrap | `<n>` | `<n>` | `+<n>/-<n>` | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `<n>h<n>m<n>s` | `$<n>` (`<model>`) | `$<n>` | `$<n>` |
| `<waves>-<name>` | review | `<n>` | `<n>` | `+<n>/-<n>` | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `<n>h<n>m<n>s` | `$<n>` (`<model>`) | `$<n>` | `$<n>` |
| `<waves>-<name>` | port | `<n>` | `<n>` | `+<n>/-<n>` | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `<n>h<n>m<n>s` | `$<n>` (`<model>`) | `$<n>` | `$<n>` |
| `<subject>` UB pass | ub | — | — | — | — | — | — | `<n>h<n>m<n>s` | `$<n>` (`<model>`) | — | — |
| orchestrator | orchestration | `<n>` | `<n>` | — | — | — | — | — | `$<n>`+ (`<model>`) | — | — |
| **Σ recorded agents** |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`<n>h<n>m`** | **`$<n>`** | **`$<n>`** | **`$<n>`** |

## Raw lifetime discovery

`<provider>/<model>` via `<backend>`.

| tier | symbols submitted | strategies | CDropped | CCloned | CLenDropped | CLenCloned | $ | wall |
|---|---|---|---|---|---|---|---|---|
| void | `<n>` | `<n>` | `<n>` | `<n>` | `<n>` | `<n>` | `$<n>` | `<n>m<n>s` |
| string | `<n>` | `<n>` | `<n>` | `<n>` | `<n>` | `<n>` | `$<n>` | `<n>m<n>s` |
| **Σ** | **`<n>`** | **`<n>`** | **`<n>`** | **`<n>`** | **`<n>`** | **`<n>`** | **`$<n>`** | **`<n>m<n>s`** |

### Review, in-model

`<provider>/<model>` via `<backend>`.

| tier | symbols | batches | $ | wall |
|---|---|---|---|---|
| void | `<n>` | `<n>` | `$<n>` | `<n>h<n>m` |
| string | `<n>` | `<n>` | `$<n>` | `<n>h<n>m` |
| **Σ** | **`<n>`** | **`<n>`** | **`$<n>`** | **`<n>h<n>m`** |

### Review, independent

`<provider>/<model>` via `<backend>`.

| symbols | rv loc | rv $ | rv wall | rv $/symbol |
|---|---|---|---|---|
| `<n>` | `+<n>/-<n>` | `$<n>` | `<n>m<n>s` | `$<n>` |
| **Σ `<n>`** | **`+<n>/-<n>`** | **`$<n>`** | — | **`$<n>`** |

## Target set

### Batches — types, wrap

`<provider>/<model>` via `<backend>`.

| wave | batch | types | fields | lifecycle prims | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | $ | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<n>`|`<n>`| `<n>` | `<n>` | `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `$<n>` | `<n>m<n>s` | `$<n>` | `$<n>` |
|`<n>`|`<n>`| **Σ `<n>`** | **`<n>`** | **`<n>`** |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| **`$<n>`** | — | **`$<n>`** | **`$<n>`** |

### Batches — types, port

`<provider>/<model>` via `<backend>`.

| wave | batch | types | fields | lifecycle prims | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | $ | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<n>`|`<n>`| `<n>` | `<n>` | `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `$<n>` | `<n>m<n>s` | `$<n>` | `$<n>` |
|`<n>`|`<n>`| **Σ `<n>`** | **`<n>`** | **`<n>`** |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| **`$<n>`** | — | **`$<n>`** | **`$<n>`** |

### Batches — review types

`<provider>/<model>` via `<backend>`.

| wave | batch | types | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | rv loc | rv $ | rv wall | rv $/type |
|---|---|---|---|---|---|---|---|---|---|---|
|`<n>`|`<n>`| `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `+<n>/-<n>` | `$<n>` | `<n>m<n>s` | `$<n>` |
|`<n>`|`<n>`| **Σ `<n>`** |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| **`+<n>/-<n>`** | **`$<n>`** | — | **`$<n>`** |

### Batches — symbols

`<provider>/<model>` via `<backend>`.

| wave | batch | objective | symbols | loc | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | $ | wall | $/symbol | $/loc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<n>`|`<n>`| wrap | `<n>` | `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `$<n>` | `<n>m<n>s` | `$<n>` | `$<n>` |
|`<n>`|`<n>`| port | `<n>` | `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `$<n>` | `<n>m<n>s` | `$<n>` | `$<n>` |
|`<n>`|`<n>`| **Σ** | **`<n>`** | **`<n>`** |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| **`$<n>`** | | **`$<n>`** | **`$<n>`** |

### Batches — review symbols

`<provider>/<model>` via `<backend>`.

| wave | batch | symbols | +LoC | +UB tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) | rv loc | rv $ | rv wall | rv $/symbol |
|---|---|---|---|---|---|---|---|---|---|---|
|`<n>`|`<n>`| `<n>` |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| `+<n>/-<n>` | `$<n>` | `<n>m<n>s` | `$<n>` |
|`<n>`|`<n>`| **Σ `<n>`** |`+<n>/-<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)| **`+<n>/-<n>`** | **`$<n>`** | — | **`$<n>`** |

## Safety audit

Deterministic `crustify-audit unsafe`; no model.

### Snapshots

| | before review (`<sha>`) | after review (`<sha>`) |
|---|---|---|
| unsafe loc | `<n>` | `<n>` |
| % of loc | `<n>`% | `<n>`% |
| blocks | `<n>` | `<n>` |
| % in `impl T` | `<n>`% | `<n>`% |
| `unsafe fn` | `<n>` | `<n>` |
| ...of which not sanctioned | `<n>` | `<n>` |
| raw-ptr smell | `<n>` | `<n>` |
| void-ptr smell | `<n>` | `<n>` |
| FFI calls | `<n>` | `<n>` |
| `&`/`&mut` on a wrapper | `<n>` | `<n>` |
| field proj outside an accessor | `<n>` | `<n>` |

### All metrics

| metric | before | after | Δ | reading |
|---|---|---|---|---|
| `code_lines` | `<n>` | `<n>` | `<n>` | union of HIR definition spans (denominator); `cfg`-disabled items excluded |
| `total_stmts` | `<n>` | `<n>` | `<n>` | statements |
| `unsafe_blocks` | `<n>` | `<n>` | `<n>` | count of `unsafe { }` blocks, macro-expanded included |
| `unsafe_block_stmts` | `<n>` | `<n>` | `<n>` | statements inside them |
| `unsafe_block_lines` | `<n>` | `<n>` | `<n>` | their lines, every outermost block |
| `unsafe_block_code_lines` | `<n>` | `<n>` | `<n>` | **`<n>`% → `<n>`%** |
| `unsafe_blocks_wrapper_impl` | `<n>` | `<n>` | `<n>` | inside `impl <wrapper T>` |
| `unsafe_blocks_ffi_export` | `<n>` | `<n>` | `<n>` | inside the C-ABI gateway |
| `unsafe_fns` | `<n>` | `<n>` | `<n>` | `unsafe fn` declarations, post-expansion |
| `unsafe_fns_seam` | `<n>` | `<n>` | `<n>` | ...the sanctioned subset |
| **`unsafe fn` smell** | **`<n>`** | **`<n>`** | **`<n>`** | the remainder — read each and accept or fix it |
| `unsafe_fns_pub` | `<n>` | `<n>` | `<n>` | ...of `unsafe_fns`, exported from the crate |
| `unsafe_impls` / `unsafe_traits` | `<n>` / `<n>` | `<n>` / `<n>` | `<n>` | lifecycle contracts asserted once per type |
| `ffi_calls` | `<n>` | `<n>` | `<n>` | calls to a foreign item — the unsafe-FFI-call surface |
| `wrapper_newtypes` | `<n>` | `<n>` | `<n>` | LAYOUT newtypes — `repr(transparent)` over a `repr(C)` type by value, detected structurally |
| `wrapper_newtypes_declared` | `<n>` | `<n>` | `<n>` | the `CCell`-declared count, for comparison |
| `wrapper_declared_nonconformant` | `<n>` | `<n>` | `<n>` | declared but failing the structural test — **target 0** |
| `wrapper_newtypes_undeclared` | `<n>` | `<n>` | `<n>` | structural but undeclared — a hand-written layout newtype |
| `raw_ptr_args` | `<n>` | `<n>` | `<n>` | raw-ptr positions in arguments |
| `raw_ptr_rets` | `<n>` | `<n>` | `<n>` | raw-ptr positions in returns |
| **total positions** | **`<n>`** | **`<n>`** | `<n>` | args + rets; disjoint, so this is the surface |
| `raw_ptr_seam` | `<n>` | `<n>` | `<n>` | sanctioned: seam fn / `mod ffi_export` / `extern "C"` / ptr-to-own-`Self` |
| **smell (total − seam)** | **`<n>`** | **`<n>`** | `<n>` | the non-seam remainder |
| `raw_ptr_wrapped` | `<n>` | `<n>` | `<n>` | **of the smell**: pointee is a C type that HAS a wrapper — the actionable defect |
| `raw_ptr_in_wrapper` | `<n>` | `<n>` | `<n>` | **of the smell**: inside a wrapper impl — the least excusable placement |
| `raw_ptr_derefs` | `<n>` | `<n>` | `<n>` | `*p` on a raw pointer (volume) |
| `ref_to_type_wrapper` | `<n>` | `<n>` | `<n>` | `&`/`&mut` on a layout newtype — **target 0** |
| `field_proj_wrapped` | `<n>` | `<n>` | `<n>` | projection VOLUME — shares one HIR shape with `addr_of!`, not a violation |
| `field_proj_outside_impl` | `<n>` | `<n>` | `<n>` | projections outside any accessor — **target 0** |
| `field_ref_wrapped` | `<n>` | `<n>` | `<n>` | `&(*p).field` — forbidden by the translator playbook — **target 0** |
| `void_ptr_sanctioned` | `<n>` | `<n>` | `<n>` | `*c_void` in a seam / `ffi_export` / `extern "C"` signature |
| `void_ptr_smell` | `<n>` | `<n>` | `<n>` | `*c_void` elsewhere; `void_ptr_sites` names each one |

## Notes

The only prose outside the setup and legend above: pitfalls, findings, and the
context each table cannot carry. One `###` subsection per finding, titled by
what it is about. Describe the EXPERIMENT and its results — a fix made to
crustify or ffibox along the way belongs in that repo's history, not here.

> Gate misses and anything the oracle and `translate` disagreed on; a wave that
> was superseded and why; what each wave's diff actually contained beyond its
> row counts; where a metric moved and what moved it; what the judge found and
> whether it held. Everything else stays in the tables.

State where the LoC figures come from, and note that all of them exclude
comments and blank lines.

`C LoC` is `wavefront query dag --name <every scheduled entity> --loc`:
the oracle's translated-LoC view, a function seed valued at its body LoC and a
type seed at its field and op count. It reports the seeds only, with no closure
expansion, so it is the C the campaign translated rather than the surface it
was drawn from. Give the defining files' and the whole target's raw totals
beside it for scale.

`Rust LoC` is counted from source over the authored `.rs` files under
`crustify/rust`, excluding anything generated into `target/`, and split by
`#[cfg(test)]` module.

Say why that non-test figure differs from the `code_lines` the Safety audit
reports. The audit measures the union of HIR definition spans, so it counts
only what sits inside an item — no `use`, `mod` or free-standing attribute
lines — and by construction cannot see `cfg`-disabled code, which is why it
yields no test figure. Its number is the right denominator for the unsafe
ratios and the wrong one for how much Rust was written; the two must not be
added.

Say plainly that the Rust-to-C ratio is not like-for-like in any measure,
because the Rust carries tests, `// SAFETY:` justifications, `ffi_export`
gateways and scaffolding with no C counterpart.

The four unit counts are de-duplicated over ENTITIES, not scheduled units: an
entity appears once, under the last objective it ran, so a type wrapped and
later ported counts as ported and never in both. Name the entities that took
both paths. Callbacks count with symbols.

Some of it is structural and belongs here every time: whether a review wave
reused the translation batches or the oracle re-batched it under distinct caps;
which units a review schedule dropped and why; which sub-campaigns the Overview
lists but no table details, and the cost that leaves unaccounted; and any column
a campaign could not fill, said once rather than left as a field of em-dashes.
