# crustify — `<target repo> / <target>`

Copy this template into the campaign checkout, then fill it as work lands.

## Settings

As answered in `crustify/CRUSTIFY.md`; a change during the campaign is in its history
and in Notes.

- **source** — `<repo>` @ `<commit>`
- **campaign** — `<port | wrap>`
- **scope** — `<scope>`
- **translate-agent** — `<provider>/<model>`, `<api | subscription>`
- **review-agent** — `<provider>/<model>`, `<api | subscription>`; objectives `<objectives>`
- **plan-agent** — `<provider>/<model>`, `<api | subscription>`; `<n>` runs
- **workload** — max-types `<n>`, max-syms `<n>`, max-loc `<n>`, parallelism `<n>`
- **review-workload** — `<caps>`
- **sanitizers** — `<variants>`
- **target-config** — `<configuration>`, `build.json` version `<n>`

## Legend

- `subsystem` / `wave` / `batch` — the batch's place in its subsystem's `schedule.json`
- `objective` — `wrap` or `port`; `pass` — `first` for a translation batch, `review` for a
  review batch; `Σ first` / `Σ review` total each pass apart
- `types` / `symbols` / `fields` — the batch's scheduled units (callbacks count as
  symbols) and its types' assigned field accessors; a review row counts what it reviewed
- `$` / `tokens` / `wall` — the agent's computed cost (API-equivalent under
  subscription), its tokens in millions as `crustify usage` reports them, and its elapsed
  time, C rebuild included; `$/<unit>` divides `$` by the row's units
- `+LoC` — the landing's Rust insertions/deletions; `loc` — its `.rs` insertions
- `cov (C/Rust)` — line coverage after the landing, all test workloads in one run: C over
  the link unit's TUs, Rust over non-test sources; a `Σ` cell is the pass's last landing
- `+UB safe tests` … `+unit tests` — the tests the landing added, with its C/Rust coverage
  change in pp
- `+lifecycle` … `+misc`, `total` — the reports a review batch filed, by kind;
  `+rejected PoCs` — those the assistant rejected on rerun, so `total` − `+rejected PoCs`
  is the confirmed defects
- safety audit columns — the Current tally's metrics, as a landing changed them
- `cost` / `review cost` / `total` — a subsystem's translation, review and combined cost;
  `subsystem wall` — first launch to final gate; `Σ recorded agents` leaves the assistant
  out, `Σ campaign` adds it, without per-unit cells
- `UB safe tests` … `Unit tests` — `#[test]` functions per suite, each with the coverage of
  running it alone; `Total tests` — all four, whose coverage is one joint run's union,
  never the sum
- `total`, `ported` and `wrapped` types and symbols — the scheduled public-API units, and
  those with a `Replaces:` or a `Wraps:` anchor at the tip

Every table below is a heading, a model line and the table. All prose belongs
in Notes.

## Overview

- **branch** — `crustify/main`, tip `<sha>`; crustify `<sha>`, ffibox `<sha>`, wavefront `<sha>`
- **C test baseline** — `<passed>/<total>`, `<n>` skipped; disabled: `<tests>`
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

| subsystem | nr types | nr symbols | subsystem wall | cost | tokens | $/type | $/sym | review cost | review tokens | review $/type | review $/sym | total | total tokens | total $/type | total $/sym |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `<link-unit>/void` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| `<link-unit>/string` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| planners | — | — | `<n>h<n>m<n>s` | — | — | — | — | — | — | — | — | `$<n>` | `<n>M` | — | — |
| assistant | — | — | — | — | — | — | — | — | — | — | — | `$<n>` | `<n>M` | — | — |
| **Σ recorded agents** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** |
| **Σ campaign** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | — | — | **`$<n>`** | **`<n>M`** | — | — | **`$<n>`** | **`<n>M`** | — | — |

## Safety audit

Deterministic `ffimap <workdir> --json`; no model. Every counter is in the `ffimap.json`
tracked in the campaign's artifact dir and in each subsystem's, wave's and batch's.

### Current tally

| metric | counters | what it counts | campaign base (`<sha>`) | current (`<sha>`) | Δ |
|---|---|---|---:|---:|---:|
| pub raw ptr (safe) | `raw_ptr_pub_safe_interface` | raw pointers on the safe public interface: public fields and safe public fns | `<n>` | `<n>` | `±<n>` |
| pub raw ptr | `raw_ptr_pub` | raw pointers anywhere on the public interface, `unsafe fn`s included | `<n>` | `<n>` | `±<n>` |
| pub void ptr | `void_ptr_ty_pub_fields_pub` + `void_ptr_fn_pub_safe` + `void_ptr_fn_pub_unsafe` | type-erased pointers left to the API's users | `<n>` | `<n>` | `±<n>` |
| pub unsafe fn | `unsafe_fns_pub` | the obligations the crate exports to its callers | `<n>` | `<n>` | `±<n>` |
| C borrow | `c_type_borrow_non_sanctioned` | Rust references into C memory outside the sanctioned handle positions; target 0 | `<n>` | `<n>` | `±<n>` |
| slice borrow | `raw_ptr_as_slice_borrow` | slices and strings borrowed over raw pointers, which C must neither free nor change | `<n>` | `<n>` | `±<n>` |
| unsafe loc % | `unsafe_loc_ratio` | unsafe block lines over code lines; context, not a score | `<n>` | `<n>` | `±<n>` pp |
| unsafe blocks | `unsafe_blocks` | unsafe blocks, the denominator of the ratio's reading | `<n>` | `<n>` | `±<n>` |
| Send/Sync | `unsafe_send_impl` + `unsafe_sync_impl` | thread safety asserted rather than derived from the fields | `<n>` | `<n>` | `±<n>` |
| C by value | Σ `c_type_by_val_*` + Σ `c_type_std_owner_*` | C types held outside an ffibox owner, which a move can leave dangling | `<n>` | `<n>` | `±<n>` |
| Drop/Clone | `drop_impl` + `clone_impl` | lifecycles written by hand rather than through an owner | `<n>` | `<n>` | `±<n>` |
| deref outside impl | `raw_ptr_derefs_outside_impl` | raw pointer dereferences outside any `impl` or trait body | `<n>` | `<n>` | `±<n>` |

## Planning

`<provider>/<model>` via `<backend>`. One row per planner run, in order; its reports are
the corrections it made to what earlier runs committed.

| run | commit | subsystems changed | items moved | wavefront artifacts changed | reports | $ | tokens | wall |
|---|---|---:|---:|---|---:|---|---|---|
| 1 | `<sha>` | `<n>` | `<n>` | `<files>` | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| 2 | `<sha>` | `<n>` | `<n>` | `<files>` | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| **Σ** | | **`<n>`** | **`<n>`** | | **`<n>`** | **`$<n>`** | **`<n>M`** | **`<n>m<n>s`** |

## Types

### Batches — wrap

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | pass | types | fields | +LoC | cov (C/Rust) | $ | tokens | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | review | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ first** |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |
| **Σ review** |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches — wrap: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | pass | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | first | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | review | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| **Σ first** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |
| **Σ review** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches — port

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | pass | types | fields | +LoC | cov (C/Rust) | $ | tokens | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | review | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ first** |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |
| **Σ review** |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches — port: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | pass | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | first | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | review | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| **Σ first** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |
| **Σ review** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches: safety audit

Deterministic `ffimap`; no model.

| subsystem | wave | batch | objective | pass | pub raw ptr (safe) | pub raw ptr | pub void ptr | pub unsafe fn | C borrow | slice borrow | unsafe loc % | unsafe blocks | Send/Sync | C by value | Drop/Clone | deref outside impl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | port | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | review | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| **Σ first** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** |
| **Σ review** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** |

### Batches — review: PoC + reports

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total | +rejected PoCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` | `<n>` |
| **Σ** |  |  | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** | **`<n>`** |

## Symbols

### Batches

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | objective | pass | symbols | loc | +LoC | cov (C/Rust) | $ | tokens | wall | $/symbol | $/loc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | port | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | review | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ first** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |
| **Σ review** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches: tests

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | pass | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | first | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | review | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| **Σ first** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |
| **Σ review** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches: safety audit

Deterministic `ffimap`; no model.

| subsystem | wave | batch | objective | pass | pub raw ptr (safe) | pub raw ptr | pub void ptr | pub unsafe fn | C borrow | slice borrow | unsafe loc % | unsafe blocks | Send/Sync | C by value | Drop/Clone | deref outside impl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | port | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | wrap | review | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` |
| **Σ first** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** |
| **Σ review** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** |

### Batches — review: PoC + reports

`<provider>/<model>` via `<backend>`.

| subsystem | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total | +rejected PoCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<subsystem>` | `<n>` | `<n>` | — | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` | `<n>` |
| **Σ** |  |  | — | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** | **`<n>`** |

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

Say why that non-test figure differs from the `code_lines` ffimap
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
