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

Review batches run by `crustify spawn-reviewer`, LLM-as-a-Judge over each landed wave.

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

## Legend

- `objective` — what the batch's agents were told to do: `wrap`, `port`, or
  `raw lifetime`. The Types tables are split by it, so it appears as a column
  only in the Symbols `Batches` table, which mixes the two
- `subsystem` — `<link-unit>/<subsystem>`, or `raw-lifetime-void` /
  `raw-lifetime-string`. In the Types and Symbols tables it names the batch's subsystem,
  the same name as its Overview row, and with `wave` and `batch` keys the row to
  `schedule.json`
- `wave` / `batch` — the batch's position in its subsystem's plan: the index
  of its wave in `waves` and of the batch within that wave's `batches`, so a
  batch row joins to `schedule.json`, to the agent that landed it, and to its
  Overview subsystem row. Schema-v2 plans carry `steps` and `plan_items`
  rather than indexed waves and batches, so historical rows leave both blank
- `types` / `symbols` — scheduler units in the batch. Callbacks are scheduled
  in symbol batches and counted there
- `fields` — in-scope fields: the field accessors the oracle assigned to that
  type batch, not the type's full declared field count
- `strategies emitted` — in `Raw lifetime discovery`, the release and clone
  strategies that tier's batch emitted for its `void` or string primitives
- `$` / `wall` / `loc` — that agent's computed cost, its elapsed time, and the
  `.rs` insertions of its landing commit. `wall` is `ended_at − started_at` from
  the agent's own `usage.json`, so it INCLUDES the per-worktree C rebuild
- `$/type` / `$/symbol` / `$/field` / `$/loc` — that row's `$` over its units,
  its in-scope fields, or its `loc`
- `tokens` / `rv tokens` / `batch tokens` / `review tokens` / `total tokens` — the
  tokens behind the `$` cell to their left, in millions: input + output + cache read +
  cache write, summed over the agent's `usage.json` requests (the figure `crustify cost`
  reports). Cache reads dominate it
- `subsystem wall` — from its first batch launch through its final review
  and regression gate
- `batch` / `review` — in the Overview, the computed cost of the subsystem's
  translation batches and of its review batches; `—` where it ran none
- `total` — `batch` + `review`; for the orchestrator, its own cost
- `orchestrator` — the Overview row for every orchestrator session of the campaign, priced
  from the `orchestrator-*.usage.json` records in its campaign dir; `total` is their sum. A
  session that died before writing its record is recovered from its transcript (Notes)
- `Σ recorded agents` / `Σ campaign` — the batch and review agents alone, then those plus the
  orchestrator. `$/type` and `$/sym` are given for the agents only, since the orchestrator's
  cost cannot be split by unit kind
- `$/type` / `$/sym` — in the Overview, a subsystem's cost over the types or
  symbols it was scheduled for; `—` where it was scheduled for none
- `+LoC` — the landed batch's Rust-source insertions/deletions relative to its
  wave's base
- `cov (C/Rust)` — in a `Batches` table, the absolute line coverage right after
  that batch landed, from ONE run of all four test workloads together (their
  union): C over the subsystem link unit's TUs in the `coverage` prebuild,
  Rust over the authored non-test sources. Its **Σ** cell is the coverage at the
  table's last landing, not a sum
- `+UB safe tests` / `+UB unsafe tests` / `+equiv tests` / `+unit tests` — in a
  `Batches …: tests` table, the tests added by that landed batch; each parenthesized pair is its C/Rust
  line-coverage change in percentage points. Negative coverage deltas are valid
  when the landed source adds more executable lines than the new tests cover
- `+lifecycle` … `+misc` — in a `Batches — review: PoC + reports` table, the
  defect reports that review batch filed under
  `crustify/reviews/<artifact-dir>/<category>/`, one per defect it reported;
  `+UB safe` / `+UB unsafe` are its `ub_safe` and `ub_unsafe` categories.
  `+lifecycle` covers type and raw-lifetime items only, so it reads `—` for
  symbols. `total` is the row's sum
- `+rejected PoCs` — the `ub_safe`, `ub_unsafe` and `equiv` PoCs that review
  batch filed which the orchestrator rejected after rerunning them: they did not
  reproduce, or did not show a real bug, and their fixes were reverted. They
  stay counted in their categories; `total` minus this column is the confirmed
  defects
- `+pub unsafe fn` / `+pub raw ptr` — the change the landed batch made to the
  public unsafe surface (`unsafe_fns_pub`) and to the raw pointers on the safe
  public interface (`raw_ptr_ty_pub_fields_pub` + `raw_ptr_fn_pub_safe`) of the unseeded
  static scan, at its landing against the commit before it; a review batch's fixes
  show as negative values
- `rv $` / `rv wall` / `rv loc` — the REVIEW agent's cost, elapsed time, and net
  `.rs` line delta (`+ins/-del`) of its landing commit. Under subscription
  billing `rv $` is an API-equivalent comparison value, not a charged amount
- `UB safe tests` / `UB unsafe tests` / `Equiv tests` / `Unit tests` — counts of
  `#[test]` functions in the `tests/ub_safe`, `tests/ub_unsafe` and `tests/equiv`
  test binaries and in the library's `#[cfg(test)]` modules. Each
  coverage pair comes from running only that workload, against the
  coverage-instrumented target C sources and authored Rust sources; state any
  excluded files or generated code in Notes. The four workloads bound different
  obligations, so report them apart and never sum them. Report the UB
  workload once, from a single coverage run on the plain build: it executes once
  per prepared sanitizer, but those runs share one test set and re-counting them
  inflates the figure. Name the instruments it ran under in Notes
- `Total tests` — the four counts added. Its coverage pair is NOT the four
  pairs added: it comes from one run of all four workloads together and is the
  union of the lines any of them reached, which is smaller than the sum wherever
  two workloads cover the same line. Deriving it arithmetically overstates it.
  It is a reach figure only — it mixes four verdict sources and so bounds no
  single obligation, which is why the four stay reported apart above it
- `total types` / `total symbols` — the units the target's public API exports, deprecated
  items excluded: every type, and every symbol and callback, scheduled across all of
  `schedule.json`, raw-lifetime items aside. They are fixed for the campaign
- `wrapped types` / `wrapped symbols` — scheduled units whose `Wraps:` or `Replaces:` anchor
  is present at the campaign tip; the parenthesized share is of `total types` /
  `total symbols`

Every table below is a heading, a model line and the table. All prose belongs
in Notes.

## Overview

- **Rust LoC, non-test** — `<n>`
- **Rust LoC, tests** — `<n>`
- **UB safe tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **UB unsafe tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Equiv tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Unit tests** — `<count of #[test]>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **Total tests** — `<sum of the four counts>` (`<n>`% C LoC coverage, `<n>`% Rust LoC coverage)
- **C LoC** — `<n>`
- **total types** — `<n>`
- **total symbols** — `<n>`
- **ported types** — `<n>`
- **ported symbols** — `<n>`
- **wrapped types** — `<n>` (`<n>`% of total types)
- **wrapped symbols** — `<n>` (`<n>`% of total symbols)

Implementation `<provider>/<model>` via `<backend>`; review
`<provider>/<model>` via `<backend>`.

| subsystem | nr types | nr symbols | subsystem wall | batch | batch tokens | review | review tokens | total | total tokens | $/type | $/sym |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `raw-lifetime-void` | `0` | `<n>` | `<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | — | `$<n>` |
| `raw-lifetime-string` | `0` | `<n>` | `<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | — | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| orchestrator | — | — | — | — | — | — | — | `$<n>` | `<n>M` | — | — |
| **Σ recorded agents** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** |
| **Σ campaign** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** | — | — |

## Raw lifetime discovery

`<provider>/<model>` via `<backend>`.

| tier | strategies emitted | $ | tokens | wall |
|---|---|---|---|---|
| void | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| string | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| **Σ** | **`<n>`** | **`$<n>`** | **`<n>M`** | **`<n>m<n>s`** |

### Review

`<provider>/<model>` via `<backend>`.

| tier | rv loc | rv $ | rv tokens | rv wall |
|---|---|---|---|---|
| void | `+<n>/-<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| string | `+<n>/-<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| **Σ** | **`+<n>/-<n>`** | **`$<n>`** | **`<n>M`** | **`<n>m<n>s`** |

## Types

### Batches — wrap

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | types | fields | +LoC | cov (C/Rust) | +pub unsafe fn | +pub raw ptr | $ | tokens | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| `<n>` | `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ** |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`±<n>`** | **`±<n>`** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches — wrap: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
| **Σ** |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — port

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | types | fields | +LoC | cov (C/Rust) | +pub unsafe fn | +pub raw ptr | $ | tokens | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| `<n>` | `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ** |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`±<n>`** | **`±<n>`** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches — port: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
| **Σ** |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — review

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | types | +LoC | cov (C/Rust) | +pub unsafe fn | +pub raw ptr | rv loc | rv $ | rv tokens | rv wall | rv $/type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `+<n>/-<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` |
| **Σ** |  |  | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`±<n>`** | **`±<n>`** | **`+<n>/-<n>`** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** |

### Batches — review: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
| **Σ** |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — review: PoC + reports

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total | +rejected PoCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` | `<n>` |
| **Σ** |  |  | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** | **`<n>`** |

## Symbols

### Batches

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | objective | symbols | loc | +LoC | cov (C/Rust) | +pub unsafe fn | +pub raw ptr | $ | tokens | wall | $/symbol | $/loc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| wrap | `<n>` | `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| port | `<n>` | `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ** |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`±<n>`** | **`±<n>`** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
| **Σ** |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — review

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | symbols | +LoC | cov (C/Rust) | +pub unsafe fn | +pub raw ptr | rv loc | rv $ | rv tokens | rv wall | rv $/symbol |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`| `<n>` |`+<n>/-<n>`| `<n>`% / `<n>`% | `±<n>` | `±<n>` | `+<n>/-<n>` | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` |
| **Σ** |  |  | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`±<n>`** | **`±<n>`** | **`+<n>/-<n>`** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** |

### Batches — review: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|
|`<link-unit>/<subsystem>`|`<n>`|`<n>`|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|`+<n>` (`+<n>`/`+<n>` pp)|
| **Σ** |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — review: PoC + reports

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total | +rejected PoCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | — | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` | `<n>` |
| **Σ** |  |  | — | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** | **`<n>`** |

## Safety audit

Deterministic `ffimap <workdir>` (`ffimap.json`); no model.

### Final tally overview

| | final (`<sha>`) |
|---|---|
| unsafe loc | `<n>` |
| % of loc | `<n>`% |
| blocks | `<n>` |
| % in `impl T` | `<n>`% |
| `unsafe fn` | `<n>` |
| ...public | `<n>` |
| raw ptrs on the safe public interface (types + safe fns) | `<n>` |
| void ptrs on the safe public interface (types + safe fns) | `<n>` |
| FFI calls | `<n>` |
| `&`/`&mut` on a wrapper | `<n>` |
| field proj outside an accessor | `<n>` |

### All metrics

| metric | final (`<sha>`) | `<link-unit>/<subsystem>` (`<sha>`) | … |
|---|---|---|---|
| `code_lines` | `<n>` | `<n>` | … |
| `total_stmts` | `<n>` | `<n>` | … |
| `safe_fns_pub` | `<n>` | `<n>` | … |
| `safe_fns_priv` | `<n>` | `<n>` | … |
| `unsafe_blocks` | `<n>` | `<n>` | … |
| `unsafe_block_stmts` | `<n>` | `<n>` | … |
| `unsafe_block_lines` | `<n>` | `<n>` | … |
| `unsafe_block_code_lines` | `<n>` | `<n>` | … |
| `unsafe_blocks_wrapper_impl` | `<n>` | `<n>` | … |
| `unsafe_blocks_ffi_export` | `<n>` | `<n>` | … |
| `unsafe_fns` | `<n>` | `<n>` | … |
| **`unsafe_fns_pub`** | **`<n>`** | `<n>` | … |
| `unsafe_fns_priv` | `<n>` | `<n>` | … |
| `unsafe_impls` / `unsafe_traits` | `<n>` / `<n>` | `<n>` / `<n>` | … |
| `ty_wrapper` | `<n>` | `<n>` | … |
| `ty_wrapper_borrow_sanctioned` | `<n>` | `<n>` | … |
| **`ty_wrapper_borrow_non_sanctioned`** | **`<n>`** | `<n>` | … |
| `ty_wrapper_by_val_fn_sig_pub` | `<n>` | `<n>` | … |
| `ty_wrapper_by_val_fn_sig_priv` | `<n>` | `<n>` | … |
| `ty_wrapper_by_val_ty_pub_fields_pub` | `<n>` | `<n>` | … |
| `ty_wrapper_by_val_ty_pub_fields_priv` | `<n>` | `<n>` | … |
| `ty_wrapper_by_val_ty_priv` | `<n>` | `<n>` | … |
| `ty_wrapper_std_owner_fn_sig_pub` | `<n>` | `<n>` | … |
| `ty_wrapper_std_owner_fn_sig_priv` | `<n>` | `<n>` | … |
| `ty_wrapper_std_owner_ty_pub_fields_pub` | `<n>` | `<n>` | … |
| `ty_wrapper_std_owner_ty_pub_fields_priv` | `<n>` | `<n>` | … |
| `ty_wrapper_std_owner_ty_priv` | `<n>` | `<n>` | … |
| `ty_non_wrapper_borrow_pub_safe` | `<n>` | `<n>` | … |
| `ty_non_wrapper_borrow_pub_unsafe` | `<n>` | `<n>` | … |
| `ty_non_wrapper_borrow_priv_safe` | `<n>` | `<n>` | … |
| `ty_non_wrapper_borrow_priv_unsafe` | `<n>` | `<n>` | … |
| **`raw_ptr_ty_pub_fields_pub`** | **`<n>`** | `<n>` | … |
| `raw_ptr_ty_pub_fields_priv` | `<n>` | `<n>` | … |
| `raw_ptr_ty_priv` | `<n>` | `<n>` | … |
| **`raw_ptr_fn_pub_safe`** | **`<n>`** | `<n>` | … |
| `raw_ptr_fn_pub_unsafe` | `<n>` | `<n>` | … |
| `raw_ptr_fn_priv_safe` | `<n>` | `<n>` | … |
| `raw_ptr_fn_priv_unsafe` | `<n>` | `<n>` | … |
| `raw_ptr_has_ty_wrapper` | `<n>` | `<n>` | … |
| `raw_ptr_derefs` | `<n>` | `<n>` | … |
| `raw_ptr_derefs_outside_impl` | `<n>` | `<n>` | … |
| `void_ptr_ty_pub_fields_pub` | `<n>` | `<n>` | … |
| `void_ptr_ty_pub_fields_priv` | `<n>` | `<n>` | … |
| `void_ptr_ty_priv` | `<n>` | `<n>` | … |
| `void_ptr_fn_pub_safe` | `<n>` | `<n>` | … |
| `void_ptr_fn_pub_unsafe` | `<n>` | `<n>` | … |
| `void_ptr_fn_priv_safe` | `<n>` | `<n>` | … |
| `void_ptr_fn_priv_unsafe` | `<n>` | `<n>` | … |
| `ty_field_proj_wrapped` | `<n>` | `<n>` | … |
| `ty_field_proj_outside_impl` | `<n>` | `<n>` | … |
| `ty_field_borrow_wrapped` | `<n>` | `<n>` | … |
| `deref_impl_on_wrapper` | `<n>` | `<n>` | … |
| `ffi_calls` | `<n>` | `<n>` | … |

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
which units a review schedule dropped and why; which subsystems the Overview
lists but no table details, and the cost that leaves unaccounted; and any column
a campaign could not fill, said once rather than left as a field of em-dashes.
