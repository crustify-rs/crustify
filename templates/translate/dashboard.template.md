# crustify — `<target repo> / <target>`

Copy this template into the campaign checkout, then fill it as work lands.

## Settings

As answered in `crustify/CRUSTIFY.md`; a change during the campaign is in its history
and in Notes.

- **source** — `<repo>` @ `<commit>`
- **campaign** — `<port | wrap>`
- **scope** — `<scope>`
- **translate-agent** — `<backend>`, `<api | subscription>`, proxy `<proxy | none>`, args `<args | none>`
- **review-agent** — `<backend>`, `<api | subscription>`, proxy `<proxy | none>`, args `<args | none>`; objectives `<objectives>`
- **plan-agent** — `<backend>`, `<api | subscription>`, proxy `<proxy | none>`, args `<args | none>`; `<n>` runs
- **workload** — `<caps | no cap>`
- **review-workload** — `<caps | no cap>`
- **sanitizers** — `<variants>`
- **target-config** — `<configuration>`, `build.json` version `<n>`
- **ship** — `<after every integrated module | after: modules | once the scope is done>`

## Legend

- `module` / `wave` / `batch` — the batch's place in `schedule.json`: its wave's module and
  the wave and batch indices
- `objective` — `wrap` or `port`, or a later stage, `port/layout`, `port/memory` or `port/unexport`; `pass` — `first` for a translation batch, `review` for a
  review batch; `Σ first` / `Σ review` total each pass apart
- `types` / `symbols` / `fields` — the batch's scheduled units, each under the route its
  `kind` selects, as the `task-schema` skill's Routes section gives it: structs, unions,
  enums, typedefs and type-generating macros are types, functions, globals, function
  pointers and other macros symbols; and the members its items' `field_users` list, a
  struct's or a union's fields and an enum's constants; a review row counts what it reviewed
- `$` / `tokens` / `wall` — the agent's computed cost (API-equivalent under
  subscription), its tokens in millions as `crustify-usage` reports them, and its elapsed
  time, C rebuild included; `$/<unit>` divides `$` by the row's units
- `+LoC` — the landing's Rust insertions/deletions; `loc` — its `.rs` insertions
- `cov (C/Rust)` — line coverage after the landing, all test workloads in one run: C over
  the link unit's TUs, Rust over non-test sources; a `Σ` cell is the pass's last landing
- `+UB safe tests` … `+unit tests` — the tests the landing added, with its C/Rust coverage
  change in pp
- `+lifecycle` … `+misc`, `total` — the reports a review batch filed, by kind
- safety audit columns — the Safety audit's metrics, as a landing changed them
- `cost` / `review cost` / `total` — a module's translation, review and combined cost;
  `module wall` — first launch to final gate; `Σ recorded agents` leaves the assistant
  out, `Σ campaign` adds it, without per-unit cells
- `UB safe tests` … `Unit tests` — `#[test]` functions per suite, each with the coverage of
  running it alone; `Total tests` — all four, whose coverage is one joint run's union,
  never the sum
- `total`, `ported` and `wrapped` types and symbols — the scheduled public-API units, and
  those with a `Replaces` or a `Wraps` anchor at the tip; `share` is of the total

Every table below is a heading, a model line, naming the model and backend its usage
records name, and the table. All prose belongs in Notes.

## Overview

- **branch** — `crustify/devel`, tip `<sha>`; `main` shipped at `<sha>`; crustify `<sha>`, ffibox `<sha>`, wavefront `<sha>`
- **C test baseline** — `<passed>/<total>`, `<n>` skipped; disabled: `<tests>`
- **Rust LoC** — `<n>` non-test, `<n>` tests; **C LoC** — `<n>`

### Coverage stats

| | count | share | C LoC coverage | Rust LoC coverage |
|---|---:|---:|---:|---:|
| UB safe tests | `<n>` | — | `<n>`% | `<n>`% |
| UB unsafe tests | `<n>` | — | `<n>`% | `<n>`% |
| Equiv tests | `<n>` | — | `<n>`% | `<n>`% |
| Unit tests | `<n>` | — | `<n>`% | `<n>`% |
| **Total tests** | **`<n>`** | — | **`<n>`%** | **`<n>`%** |
| total types | `<n>` | — | — | — |
| ported types | `<n>` | `<n>`% | — | — |
| wrapped types | `<n>` | `<n>`% | — | — |
| total symbols | `<n>` | — | — | — |
| ported symbols | `<n>` | `<n>`% | — | — |
| wrapped symbols | `<n>` | `<n>`% | — | — |

### Module stats

Implementation `<model>` on `<backend>`; review
`<model>` on `<backend>`.

| module | nr types | nr symbols | module wall | cost | tokens | $/type | $/sym | review cost | review tokens | review $/type | review $/sym | total | total tokens | total $/type | total $/sym |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `<link-unit>/<module> (foundational)` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` | `$<n>` | `<n>M` | `$<n>` | `$<n>` |
| side campaigns | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | — | — | `$<n>` | `<n>M` | — | — | `$<n>` | `<n>M` | — | — |
| planners | — | — | `<n>h<n>m<n>s` | — | — | — | — | — | — | — | — | `$<n>` | `<n>M` | — | — |
| assistant | — | — | — | — | — | — | — | — | — | — | — | `$<n>` | `<n>M` | — | — |
| **Σ recorded agents** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`$<n>`** |
| **Σ campaign** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | — | — | **`$<n>`** | **`<n>M`** | — | — | **`$<n>`** | **`<n>M`** | — | — |

## Safety audit

Deterministic `ffimap`, run as the `ffimap` skill's Accounting section describes; no
model. Every counter is in the `ffimap.json` tracked in the campaign's artifact dir, in
each wave's `waves/wave-<index>/` and in each batch run's dir. Each metric is one counter
or a combination of counters, named by their dotted paths into the scan's `counts`; a `%`
metric is a share within one record, and a `−` subtracts a share from the record it cuts.

### Metrics

| metric | counters | what it counts |
|---|---|---|
| pub raw ptr | `raw_ptr.total.safe.pub` | raw pointers a consumer meets without writing `unsafe`: public fields and the signatures of safe public fns; target 0 |
| pub void ptr | `raw_ptr.field.of_which.void.pub` + `raw_ptr.fn_sig_arg.of_which.void.{safe,unsafe}.pub` + `raw_ptr.fn_sig_ret.of_which.void.{safe,unsafe}.pub` | type-erased pointers left to the API's users, `unsafe fn`s included |
| pub unsafe fn | `fn.unsafe.pub` | the obligations the crate exports to its callers |
| &cell | `ty.ffibox.wrapper.as.borrowed.std.pub` − `….of_which.self_in_ref_accessor.pub` − `….of_which.self_in_trait_impl.pub` | public references to a cell outside the positions ffibox sanctions, where the convention wants a handle; target 0 |
| C by value | `ty.ffibox.sys.as.by_val.total` + `ty.ffibox.sys.as.owned.std.total` | C structs held by value or in a standard-library owner rather than through a cell, which a move can leave dangling |
| celled % | `ty.ffibox.sys.of_which.raw_ptr_in_sys.of_which.wrapped` / `….of_which.used` | of the C types the bindings pass by pointer that the crate uses, those a cell covers |
| raw→std | `raw_ptr.casted_to.std.total` | raw pointers turned into a standard-library borrow, slice, string or owner, whose lifetime or ownership the type system then trusts |
| unmanaged ptr types | `ty.storing_raw_ptr.of_which.none.total` | types that store a raw pointer and declare nothing about it |
| ptr Drop | `ty.storing_raw_ptr.of_which.impl_drop.total` | types that store a raw pointer and free it by hand, rather than through an owner |
| Send/Sync | `ty.impl_trait.of_which.std.send.total` + `ty.impl_trait.of_which.std.sync.total` | thread safety asserted rather than derived from the fields |
| raw deref | `raw_ptr.deref.total` | raw-pointer reads and writes in bodies, each a pointer the code vouches for |
| FFI calls | `code.unsafe_call.ffi` | calls across the C boundary, through bindings or stored function pointers |
| unsafe loc % | `code.loc.unsafe` / `code.loc.total` | lines of unsafe code over code lines; the comparable measure of unsafe volume |
| unsafe blocks | `code.unsafe_block.total` − `code.unsafe_block.of_which.ffi_export` | hand-written unsafe blocks, a port's generated export gateways left out; moves with the one-op-per-block policy, so not comparable across crates |

## Planning

`<model>` on `<backend>`. One row per planner run, in order; its reports are
the corrections it made to what earlier runs committed.

| run | modules changed | items moved | wavefront artifacts changed | reports | $ | tokens | wall |
|---|---:|---:|---|---:|---|---|---|
| 1 | `<n>` | `<n>` | `<files>` | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| 2 | `<n>` | `<n>` | `<files>` | `<n>` | `$<n>` | `<n>M` | `<n>m<n>s` |
| **Σ** | **`<n>`** | **`<n>`** | | **`<n>`** | **`$<n>`** | **`<n>M`** | **`<n>m<n>s`** |

## Side campaigns

One row per out-of-tree library the campaign wraps in a side campaign, as
the `dependencies` skill describes. Each wrapper's own dashboard, in its
`<source>-crustify` repository, is its record; its row here copies that dashboard's
figures as of the commit the campaign pins, and the `side campaigns` row of `Module stats`
sums them.

| library | repository | pin | shipped at | linked from | waves | types | symbols | wall | cost | tokens | review cost | review tokens | total | total tokens |
|---|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| `<library>` | `crustify-rs/<source>-crustify` | `<sha>` | `<sha>` | `side-campaign` | `<n>` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `<n>M` |
| `libc` | `crustify-rs/glibc-crustify` | `<sha>` | `<sha>` | `system` | `<n>` | `<n>` | `<n>` | `<n>h<n>m<n>s` | `$<n>` | `<n>M` | `$<n>` | `<n>M` | `$<n>` | `<n>M` |
| **Σ** | | | | | **`<n>`** | **`<n>`** | **`<n>`** | **`<n>h<n>m`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** | **`$<n>`** | **`<n>M`** |

## Types

### Batches

`<model>` on `<backend>`.

| module | wave | batch | objective | pass | types | fields | +LoC | cov (C/Rust) | $ | tokens | wall | $/type | $/field |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | port | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | port/layout | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | review | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ first** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |
| **Σ review** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches: tests

`<model>` on `<backend>`.

| module | wave | batch | pass | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | first | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| `<link-unit>/<module>` | `<n>` | `<n>` | review | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| **Σ first** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |
| **Σ review** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches: safety audit

Deterministic `ffimap`; no model.

| module | wave | batch | objective | pass | pub raw ptr | pub void ptr | pub unsafe fn | &cell | C by value | celled % | raw→std | unmanaged ptr types | ptr Drop | Send/Sync | raw deref | FFI calls | unsafe loc % | unsafe blocks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | port | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | review | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| **Σ first** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** |
| **Σ review** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** |

### Batches — review: PoC + reports

`<model>` on `<backend>`.

| module | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<module>` | `<n>` | `<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` |
| **Σ** |  |  | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** |

## Symbols

### Batches

`<model>` on `<backend>`.

| module | wave | batch | objective | pass | symbols | loc | +LoC | cov (C/Rust) | $ | tokens | wall | $/symbol | $/loc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | port | first | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | review | `<n>` | `<n>` | `+<n>/-<n>` | `<n>`% / `<n>`% | `$<n>` | `<n>M` | `<n>m<n>s` | `$<n>` | `$<n>` |
| **Σ first** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |
| **Σ review** |  |  |  |  | **`<n>`** | **`<n>`** | **`+<n>/-<n>`** | **`<n>`% / `<n>`%** | **`$<n>`** | **`<n>M`** | — | **`$<n>`** | **`$<n>`** |

### Batches: tests

`<model>` on `<backend>`.

| module | wave | batch | pass | +UB safe tests (+C/+Rust pp) | +UB unsafe tests (+C/+Rust pp) | +equiv tests (+C/+Rust pp) | +unit tests (+C/+Rust pp) |
|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | first | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| `<link-unit>/<module>` | `<n>` | `<n>` | review | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) | `+<n>` (`+<n>`/`+<n>` pp) |
| **Σ first** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |
| **Σ review** |  |  |  | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** | **`+<n>` (`+<n>`/`+<n>` pp)** |

### Batches: safety audit

Deterministic `ffimap`; no model.

| module | wave | batch | objective | pass | pub raw ptr | pub void ptr | pub unsafe fn | &cell | C by value | celled % | raw→std | unmanaged ptr types | ptr Drop | Send/Sync | raw deref | FFI calls | unsafe loc % | unsafe blocks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | port | first | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| `<link-unit>/<module>` | `<n>` | `<n>` | wrap | review | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` | `±<n>` pp | `±<n>` |
| **Σ first** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** |
| **Σ review** |  |  |  |  | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>`** | **`±<n>` pp** | **`±<n>`** |

### Batches — review: PoC + reports

`<model>` on `<backend>`.

| module | wave | batch | +lifecycle | +unsafe | +UB safe | +UB unsafe | +equiv | +internal | +conventions | +misc | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<link-unit>/<module>` | `<n>` | `<n>` | — | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `+<n>` | `<n>` |
| **Σ** |  |  | — | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`+<n>`** | **`<n>`** |

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

`Rust LoC` is counted from source over the authored `.rs` files of the workspace, `src/`,
`tests/` and the hand-written parts of `ffi/`, excluding anything generated into `target/`,
and split by
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
later ported, or given its native layout by its `port/layout`, counts as ported
and never in both. Name the entities that took both paths. Each counts under its
route, as the legend gives it.

Some of it is structural and belongs here every time: how each wave's batches
were packed, and why: their sizes, the caps if any, the waves that shared
batches, the wrap batches bound ahead of their consumers and the batches packed
again after a failure; whether review batches took each translation batch alone
or several, and how large; which modules the Overview
lists but no table details, and the cost that leaves unaccounted; and any column
a campaign could not fill, said once rather than left as a field of em-dashes.
