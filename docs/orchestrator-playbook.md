# Orchestrator playbook

The orchestrator sets up the campaign, schedules batches, monitors agents,
lands and reviews waves, runs regression gates, promotes verified tips, and
records results. Translators implement their assigned worklists.

## Artifacts

- `crustify/.gitignore` — excludes machine-local configuration, caches, builds,
  logs, and generated analysis output.
- `crustify/build.json` — records the versioned configure, build, and test
  commands.
- `crustify/subsystems.json` — records link units and subsystems, their objective,
  contents, and imported dependencies; governs the shape the Rust tree mirrors.

- `crustify/campaigns/<campaign-id>/schedule.json` — records the campaign's
  total execution order and every projected batch; tracked.
- `crustify/campaigns/<campaign-id>/<link-unit>/<subsystem>/<plan-name>.json`
  — records one sub-campaign's generated wave and batch plan; tracked.
- `…/wave-<index>/batch-<index>.json` — the thin batch projected for one agent.
- `…/wave-<index>/logs/<batch-id>.log` — one agent's output stream.
- `…/wave-<index>/logs/<batch-id>.usage.json` — one agent's token, cost, and
  wall-time record.

Read the corresponding example in `specs/` and schema description in `docs/schemas` before
creating an artifact. 

## Directory structure

```text
crustify/campaigns/<campaign-id>/
├── schedule.json
└── <link-unit>/
    └── {<subsystem>, raw-lifetime-{void, string}}/
        ├── <plan-name>.json
        └── wave-{<index>, void, string}/
            ├── batch-<index>.json
            └── logs/
                ├── <batch-id>.log
                └── <batch-id>.usage.json
crustify/rust/
crustify/tmp/
```

A sub-campaign is a subsystem, so it nests under the link unit that contains
it: `(link_unit, subsystem)` is the globally addressable identity, and the two
levels of directory are that pair. Raw-lifetime discovery has no subsystem of
its own and occupies the same level under its link unit.

`<campaign-id>` names the campaign, normally the CLI target's slug — a root
target gives `crustify/campaigns/`, `ssl/statem` gives
`crustify/campaigns/ssl/statem/`.

`schedule.json` is the campaign's total execution order and its projected
batches; see `docs/schemas/schedule.md`. Each `<plan-name>.json` is one
sub-campaign's objective-neutral plan from `wavefront schedule`, the input it
is projected from; see `docs/schemas/wave.md`.

Every path under a campaign is derived from
`(campaign-id, link-unit, subsystem, index)`, so nothing records one. Wave
directories take the campaign-global `index`, which makes them unique across
the campaign; a wave's `logs/` is what its batches receive through `--output`.
Wave indices follow executable wave order, not individual DAG layers.

## Phase 1: setup

### 1. Provision dependencies

Required dependencies:

- Python 3.13 or newer;
- Rust stable with `cargo` and `clippy`;
- Rust nightly with `rustc-dev` and `llvm-tools`;
- `bindgen-cli`;
- supported agent backends;
- Crustify;


### 2. Artifact tree scaffolding

```bash
mkdir -p <repo>/crustify
cp specs/gitignore <repo>/crustify/.gitignore
mkdir -p <repo>/crustify/campaigns/<campaign-id>
```

If you're working in a git repo, create the campaign branch:

```bash
git -C <repo> checkout -b crustify/<target>-<language-model>
```


### 3. Prebuilds and test baselines

Create immutable builds of the target so that translator agents can reuse
them:

- plain build for the functional baseline;
- coverage-instrumented build for campaign measurements.

A Rust- or bindgen-only change may reuse a matching build. A change to the compiled
target requires a private build; refresh shared builds after that change lands.

Create `crustify/build.json` from `specs/build.json`.
Increment `version` whenever any command changes.
Disable deprecated features unless otherwise instructed by the user.
Use parallel builds.
Disable unstable baseline tests as needed, record pass/total and every disabled
test in the campaign results.
Post-campaign results must match this baseline.


### 4. Subsystem decomposition

Create `crustify/subsystems.json` from `specs/subsystems.json`; see
`docs/schemas/subsystems.md`.

Use actual linker outputs to identify link units. Cover the selected target and
its complete imported producer closure. Assign every translation unit
to one subsystem; headers may be shared by multiple subsystems.

Assign one of the following objectives to each subsystem using these rules:

- `port`: project-specific behaviour or invariants to implement in Rust;
- `wrap`: generic facilities kept behind a safe Rust API over the C; and
- split mixed subsystems so project-specific code and generic facilities carry
  separate objectives.

For a wrap campaign, all subsystems carry the wrap objective.
For a port campaign, the subsystems that are project-specific carry the port
objective, while those that have Rust-native alternatives stay wrap, only to
facilitate their Rust consumers to stay interoperable with the remaining
C/C++ ones (in an intermediary state of an incremental translation) until
they can be fully nativized. Record any well established Rust crate or `std`
facility that could replace a subsystem outright in its
`rust_native_equivalent`, in descending order of fit. Before leaning on one,
verify its semantics, platform support, performance and licensing.

Aggregate each consumer-to-producer relation into one `imported_deps` record
with its `nr_edges` and the item kinds consumed across them, splitting in-tree
destinations from out-of-tree libraries. Record the graph as it is, cycles included.


### 5. Sub-campaign planning

Plan only link units and subsystems included in the campaign scope established
by the user.

Each ordinary sub-campaign translates one subsystem of one link unit from
`subsystems.json`. Raw-lifetime discovery is the only synthetic sub-campaign.

Execute link unit and subsystem sub-campaigns bottom-up, producers before
consumers. Turn the tree of link units and subsystems into a DAG, removing its
cyclic edges; use `subsystemA.imported_deps.subsystemB.nr_edges` as the descriminator
for determining producer->consumer ordering, a smaller value making the left-hand
side a producer for the right-hand side consumer.

In a port campaign, each subsystem gets a Rust-side sub-dir and top-level sub-module in their
link unit: `rust/<repo>/<link-unit>/<subsystem>/<subsystem>.rs`; TUs and headers become
sub-modules of their subsystem. In a wrap campaign subsystems don't appear as sub-modules;
TUs and headers are top-level modules directly on their link unit.

Run raw-lifetime sub-campaigns first.

Skip sub-campaigns or waves when resuming a campaign that already completed them.

### 2. Assign execution objectives

For a wrap campaign, every batch uses `objective: wrap`.

For a port campaign:

- a selected symbol uses `port` immediately;
- a selected type uses `wrap` while C reads its fields, then `port` after those
  readers are removed;
- a dependency outside the selected migration set uses `wrap`; and
- a filled anchor may be revisited only when escalating that item to `port` or
  running `review`.

Wavefront schedules are objective-neutral. The orchestrator adds the execution
objective to each projected batch, and records it there rather than on the
wave: one wave can hold batches of differing objectives, which is exactly what
the type rule above produces.


### 5. Rust tree scaffolding

Generally, the target's filesystem is the placement spec.
Mirror the following layout, all relative to `<repo>/crustify/rust/`:

- `Cargo.toml` - top-level virtual manifest.
- `<link-unit>-sys` - raw bindings package, one per link unit.
- `<repo>/` - safe repo package, one for the whole repo.
- `<repo>/<link-unit>/` - one sub-dir per link unit, cfg-gated mod in `lib.rs`.


Create minimal `Cargo.toml` and crate roots using the established conventions.
Do this only for the link units included in the scope established by the user.
Scaffold source files lazily before spawning translator agents.  

For each `-sys` package, author the build scripts required by bindgen so that translator
agents can reuse them; each  `-sys` crate needs `Cargo.toml`, `src/lib.rs`, `build.rs`,
and bindgen input. Allowlists are populated by translators lazily.


Commit the initial Rust tree on the campaign branch.


### 6. Side campaigns

TODO


## Phase 2: translation


### 3. Preflight agentic stages

Before translation, review, or UB-audit agents start:

1. resolve the selected model to its provider and backend;
2. verify the backend executable on the stage process's `PATH` and run
   `--version`;
3. verify required credential variables without printing their values;
4. reject unsupported provider and billing combinations;
5. run the stage dry-run; and
6. compare unit, wave, and batch counts with the approved schedule.

A launch succeeds only after every expected process is live, its log exists,
and the backend emits a model handshake or first repository action. On an
immediate backend, authentication, or routing failure, stop the wave, repair
the environment, and restart the same batch set.

Attach a completion monitor to every process. On exit, verify status, log,
usage record, landed commit, and worktree state. A detached process without a
monitor is not an active stage.

### 4. Prepare a sub-campaign and wave

Before the sub-campaign starts:

1. verify reusable C-build provenance;
2. generate its schedule with the narrow configuration and approved caps;
3. verify config hash, counts, barriers, and batch identities;
4. name each scheduled item's authored `.rs` home in its batch;
5. create and connect any module a batch names but the tree lacks;
6. compile the affected crates; and
7. record the canonical tip as wave zero's base.

For each recorded wave:

- create the unchecked-out integration branch
  `crustify/wave/<campaign-id>/<link-unit>/<subsystem>/wave-<index>`;
- create its log directory under the campaign; and
- write each `schedule.json` batch entry out to its `batch-<index>.json`
  verbatim, changing no field and no membership.

Branch and directory carry the same `(link_unit, subsystem)` pair, so a wave's
branch, its batches and its logs are addressable from its `schedule.json`
entry alone.

The thin batch format is:

```json
{
  "objective": "wrap",
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "type",
      "field_anchors": ["data", "linesize"],
      "home": "crustify/rust/libavutil/src/frame.rs"
    }
  ]
}
```

See `docs/schemas/batch.md` for field meaning, routing and the raw-lifetime
rule. Every field shown is required; do not add route, wave, branch, log, or
dependency fields.

Example commands:

```bash
wavefront <repo_root> --config <sub-campaign-config> schedule \
  --output <wave-plan.json> --name <items...> \
  [--transitive] [--api-headers-only] \
  [--max-syms N] [--max-loc N] [--max-types N] [--min-fields N]

crustify <repo_root> <target> translate <batch.json> \
  --base-branch <wave-branch> --output <wave-log-dir> --dry-run
```

Do not restructure the Rust tree during a wave: a batch names homes that must
still exist when its agent starts. After parallel landings, union conflicting
`-sys` allowlist additions and retest the affected crates.

Scaffold the batches' source files:


Rust has no headers, migrate them using the following rules:
- for a wrap campaign: each public header gets its own `mod` and `.rs`. 
- for a port campaign:
  - a subsystem's headers and translation units share one module;
  - a TU and its companion header share a sub-module in their subsystem;
  - headers that export implementation (e.g. `static inline` functions)
  which logically do not belong to any TU get their own `_h.rs` sub-module;
  headers shared by multiple subsystems become sub-modules for each subsystem;

### 5. Execute and monitor batches

Run one CLI process per batch, concurrently up to approved parallelism. The
harness creates `crustify/batch/<batch-id>` and an isolated worktree from the
wave branch. It links ignored shared campaign state, starts the backend, and
writes the agent stream and usage record.

The translator commits its changes and atomically fast-forwards the wave
branch. On rejection, it rebases its own branch onto the current wave tip,
revalidates, and retries. Failed translators retain their branches and
worktrees. The orchestrator must not translate the failed worklist or discard a
competing landing.

Verify every batch's exit status, log, usage record, landed commit, and cleaned
worktree before review.

### 6. Review, scan, and promote

Every translated wave requires agentic review before a consumer starts.
Reviewers must inspect the merged wave for ownership, lifetime, thread-safety,
error-mapping, and C-equivalence failures; add focused regressions; fix the
findings; and land through the same branch flow.

Use the translated item projections with `objective: review`. Default to the
translation batch caps. If review caps differ, ask Wavefront to rebatch the
exact translated identities without expanding their closure, then execute all
review waves in order.

After review lands:

1. verify all translation and review batch records;
2. build and test Rust;
3. build and test C when C changed;
4. run the feature-enabled baseline for port work;
5. run the deterministic safety scan; and
6. promote the reviewed wave tip to the canonical campaign branch.

Run the deterministic scan with the exact scheduled C names:

```bash
crustify <workdir> audit unsafe --name <wave names...> --json
```

Inspect each source site. Fix unsafe wrapper bypasses and unsound references.
Keep necessary FFI seams with a safety justification. The generated
`crustify/audit/unsafe.json` is ignored.

Do not run a generic end-of-sub-campaign review after every wave has already
been reviewed. Add one only for a named cross-wave obligation.

At campaign end, record an unseeded scan:

```bash
crustify <workdir> audit unsafe --json
```

### 7. Optional UB audit

Run `crustify <workdir> audit ub` only with explicit user approval. Run it once after the
campaign unless the user requests another milestone or a confirmed finding
blocks progress.

The UB agent must:

- create a dedicated target-repository branch;
- produce evidence and a focused regression;
- implement the repair;
- run affected builds and tests;
- rerun the reproducer; and
- commit without merging.

Independently inspect the diff and rerun the build, tests, and reproducer. Merge
only a confined patch for a confirmed finding with green evidence. Otherwise
leave the branch unmerged and report the failed gate.

### 8. Accounting

Run `crustify ... cost` over the `<batch-id>.usage.json` files. Use its computed
cost and token counts, not provider-reported dollar totals. Record agent wall
times from usage files. Record wave wall time from first batch launch through
final review and regression completion. Fill the user's evaluation table.

Fill it per batch too, for translation and review alike. Key each row by the
`wave` and `batch` index of its entry in the sub-campaign's `waves.json`; a
review batch uses its own review plan's indices. Take `$` and `wall` from that
batch's `usage.json`, never apportioned from a total. Take `+LoC` and the three
test deltas from its landing commit against its parent. The `(+C/+Rust pp)`
pair needs a coverage run per workload per commit: measure it when affordable,
otherwise leave every per-batch pair blank and say so once in Notes.

## Self-repair

When a campaign exposes a defect in Crustify, Wavefront, or ffibox, create a dedicated branch and worktree in that component's repository.
Implement and validate the reusable fix there; do not mix it into campaign
translation commits.


## To be moved


- ASan + UBSan build for FFI and lifecycle tests;
- TSan build for race tests; do not combine it with ASan;
- BSan build when BorrowSanitizer is available; and
Miri does not need a C build and cannot call the foreign library.

### 6. Configure campaign-wide source analysis

Create `crustify/wavefront/wavefront-config.json` from Wavefront's specification.
It contains:

| key | contents |
|---|---|
| `impl_files` | implementation sources and private defining headers |
| `api_headers` | published API headers |

A directory entry ends with `/`. Uncompiled candidates are removed by T1
anchoring.

Selection rules:

- `impl_files` and `api_headers` seed the implementation graph.
- An entity is targeted when its definition is in a named file. For an entity
  without a body, all declarations must be in named files.
- Headers outside the implementation tree must be named when they define
  target types.
- Add a header to `api_headers` only when its implementors are in `impl_files`.
- Dependencies merely used by the target enter the imported closure.
- `--api-headers-only` selects declarations published by `api_headers` and
  does not walk bodies.
- A struct defined in `api_headers` retains field layout. A forward declaration
  remains opaque.
- `--transitive` adds signature dependencies.
- `targeted` and `imported` describe ownership; `api` describes publication.
  These sets intersect.
- `out_of_scope.paths` changes selection. `out_of_scope.features` is
  documentation only.

Verify the configuration:

```bash
wavefront <repo_root> --config <campaign-config> query files --targeted-only
wavefront <repo_root> --config <campaign-config> query files --imported-only
```

Wavefront does not create the parent directory for `schedule --output`.

## Required deps

Wavefront and ffibox are checkouts under the data prefix of the environment
crustify is installed in — `<prefix>/share/wavefront` and
`<prefix>/share/ffibox`. Crustify resolves them there itself; you configure no
paths. A checkout already present at either location is provisioned: do not
clone or reinstall it. `CRUSTIFY_DEP_WAVEFRONT` / `CRUSTIFY_DEP_FFIBOX`
override one of them for a checkout kept elsewhere.