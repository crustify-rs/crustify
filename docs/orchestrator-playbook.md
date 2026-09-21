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

- `crustify/campaigns/<target>/<sub-campaign>/<wave-name>.json` — records the
  generated wave and batch plan; should be tracked.
- `crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/<batch-id>.log`
  — contains one agent's output stream.
- `crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/<batch-id>.usage.json`
  — contains one agent's token, cost, and wall-time record.

Read the corresponding example in `specs/` and schema description in `docs/schemas` before
creating an artifact. 

## Directory structure

```text
crustify/campaigns/<target>/
├── raw-lifetime-{void, string}/
│   └── wave-{void, string}.json
│   └── wave-{void, string}/
│       └── logs/
│           ├── <batch-id>.log
│           └── <batch-id>.usage.json
├── <sub-campaign>/
│   ├── wave-<index>.json
│   └── wave-<index>/
│       └── logs/
│           ├── <batch-id>.log
│           └── <batch-id>.usage.json
└── ...
```

`<target>` is the repository-relative CLI target. A root target uses
`crustify/campaigns/`; `ssl/statem` uses `crustify/campaigns/ssl/statem/`.

Number the schedule's `waves` array from zero. For each wave, pass its `logs/`
directory to every batch through `--output`. Wave indices follow executable
wave order, not individual DAG layers.

## Phase 1: setup

### 1. Provision dependencies

Required dependencies:

- Python 3.13 or newer;
- Rust stable with `cargo` and `clippy`;
- Rust nightly with `rustc-dev` and `llvm-tools`;
- `bindgen-cli`;
- supported agent backends;
- Crustify;


### 2. Bootstrap `crustify/`

```bash
mkdir -p <repo>/crustify
cp specs/gitignore <repo>/crustify/.gitignore
```

### 3. Create `build.json` and record the baseline

Create `crustify/build.json` from `specs/build.json`.
Increment `version` whenever any command changes.
Disable deprecated features unless otherwise instructed by the user.
Use parallel builds.
Disable unstable baseline tests as needed, record pass/total and every disabled
test in the campaign results.
Post-campaign results must match this baseline.

### 5. Prepare reusable C builds

Create immutable builds for the exact C revision, `build.json`
version, compiler, and instrumentation, so that translator agents can reuse
them:

- plain build for the functional baseline;
- coverage build for campaign measurements.

A Rust- or bindgen-only change may reuse a matching build.
A change to compiled C or a compiled shim requires a private build; refresh
shared builds after that change lands.

After each reviewed wave, run the sanitized regression gate. Measure
UB, equivalence, and unit coverage separately; do not sum them.

### 7. Create `subsystems.json`

Create `crustify/subsystems.json` from `specs/subsystems.json`; see
`docs/schemas/subsystems.md`.

Use actual linker outputs to identify link units. Cover the selected target and
its complete imported producer closure. Assign every file — translation unit
or header — to one subsystem. Keep each subsystem entirely one objective.

Use these objective rules:

- `port`: project-specific behaviour or invariants to implement in Rust;
- `wrap`: generic facilities kept behind a safe Rust API over the C; and
- split mixed subsystems so project-specific code and generic facilities carry
  separate objectives.

Record any well established Rust crate or `std` facility that could replace a
subsystem outright in its `rust_native_equivalent`, in descending order of fit.
Before leaning on one, verify its semantics, platform support, performance and
licensing. Naming a candidate does not by itself change the objective: it is
the usual reason to leave a generic facility wrapped during a partial
migration.

Aggregate each consumer-to-producer relation into one `imported_deps` record
with its `nr_edges` and the item kinds consumed across them, splitting in-tree
destinations from out-of-tree libraries.

Record the graph as it is, cycles included. Never remove a real dependency
edge, and do not rehome or merge subsystems to flatten one: this artifact
describes the decomposition, and a cycle hidden here is a cycle nothing
downstream can see. Cut cycles when you schedule, where the cut is recorded as
an explicit SCC cut in the wave plan that made it. Prefer the side with higher
incoming producer weight when selecting a boundary.

### 8. Scaffold the Rust tree

Mirror the subsystem decomposition in `subsystems.json`. The filesystem is the
placement spec: a module exists because a subsystem does, and there is no
separate document to author or keep in step with it. Rust has no headers, so a
subsystem's headers and translation units share one module.

- Create one wrapper crate for the selected in-tree target. Place its link
  units and subsystems in Rust modules so internal APIs can remain
  `pub(crate)`.
- Create one companion target `-sys` crate for the C ABI used by that wrapper,
  even when the target spans several native link units.
- Create a separate wrapper and `-sys` crate for each imported library. Reuse a
  suitable maintained Rust crate instead when its contract matches.
- Split an in-tree target into multiple wrapper crates only when its components
  are independently consumable public libraries or require incompatible build
  boundaries. Do not split solely because the C build emits multiple link
  units.
- Derive each crate's Cargo dependencies from the `imported_deps` that cross
  crate boundaries; edges internal to a crate stay between its modules.
- Create the module tree, empty: a module per subsystem, and nothing homed in
  it yet. A batch names the `.rs` home of every item it schedules, so the
  module must exist before the wave that fills it.
- Create minimal `Cargo.toml` and crate roots using `conventions.md`.
- Each `-sys` crate needs `Cargo.toml`, `src/lib.rs`, `build.rs`, and bindgen
  input.
- Its agent-owned allowlist must compile while empty.

Run:

```bash
cargo build
cargo test
```

Commit the initial Rust tree on `crustify/<target>-<model>`.

### Setup gate

Before the first wave, verify:

- baseline pass/total and disabled tests are recorded;
- T1 and T2 directories are populated;
- the per-objective file queries match the approved scope;
- every `-sys` crate builds, links, and tests; and
- `query dag --layer 0` returns the producer leaf set.

## Phase 2: translation

### 1. Plan sub-campaigns

Each ordinary sub-campaign translates one subsystem from `subsystems.json`.
Raw-lifetime discovery is the only synthetic sub-campaign.

Before scheduling a subsystem, create
`crustify/campaigns/<target>/<sub-campaign>/wavefront-config.json`. Its
`impl_files` and `api_headers` must be exact subsets of the campaign-wide
configuration. Use the campaign-wide configuration only for campaign-wide work
such as raw-lifetime discovery.

Scheduling rules:

- Wrap campaigns use `schedule --api-headers-only`.
- Prefer `--transitive` so the sub-campaign includes the selected surface's
  in-scope producer dependencies. Use an exact non-transitive selection only
  when those dependencies are already satisfied or intentionally excluded.
- Accept Wavefront's closure, dependency layers, waves, and batches. Do not
  infer or regroup them manually.
- Execute subsystem sub-campaigns bottom-up.
- A consumer waits until every producer wave passes review and promotion.
- Order simultaneously ready roots by `(link_unit, subsystem)`; use producer
  weight only as a tie-breaker.
- Batch caps limit agent work. Do not impose another subsystem-size budget.
- Omit completed items from later schedules.

Run raw-lifetime sub-campaigns first:

1. `schedule --lifetime-for void`, then translate and review every wave;
2. `schedule --lifetime-for string`, then translate and review every wave.

Skip either only when resuming a campaign that already completed it.

### 2. Assign execution objectives

For a wrap campaign, every batch uses `objective: wrap` and every ordinary
schedule uses `--api-headers-only`.

For a port campaign:

- a selected symbol uses `port` immediately;
- a selected type uses `wrap` while C reads its fields, then `port` after those
  readers are removed;
- a dependency outside the selected migration set uses `wrap`; and
- a filled anchor may be revisited only when escalating that item to `port` or
  running `review`.

Wavefront schedules are objective-neutral. The orchestrator adds the execution
objective to each projected batch.

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
  `crustify/wave/<target-slug>/<sub-campaign>/wave-<index>`;
- create its log directory under the campaign; and
- project each recorded batch without changing its membership.

The thin batch format is:

```json
{
  "objective": "wrap",
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "type",
      "field_anchors": ["data", "linesize"]
    }
  ]
}
```

Allowed kinds are `type`, `symbol`, `callback`, and `raw-lifetime`. A
raw-lifetime batch contains one `void` or `string` item with `defined_in: null`.
Other items require a definition path. Only types have non-empty
`field_anchors`. Do not add route, wave, branch, log, or dependency fields.

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

- `crustify/wavefront/wavefront-config.json` — defines the campaign-wide source
  inventory.
- `crustify/wavefront/ownership-store.json` — stores authored semantic findings.
- `crustify/wavefront/codeql/t1/*.csv` — contains extracted entity records.
- `crustify/wavefront/codeql/t2/*.csv` — contains extracted dependency edges.
- `crustify/campaigns/<target>/<sub-campaign>/wavefront-config.json` — narrows
  source inventory to one sub-campaign.


- ASan + UBSan build for FFI and lifecycle tests;
- TSan build for race tests; do not combine it with ASan;
- BSan build when BorrowSanitizer is available; and
Miri does not need a C build and cannot call the foreign library.


## Directory structure

```text
crustify/campaigns/<target>/
├── raw-lifetime-void/
│   ├── wavefront-config.json
│   └── wave-void.json
├── raw-lifetime-string/
│   ├── wavefront-config.json
│   └── wave-string.json
├── <sub-campaign>/
│   ├── wavefront-config.json
│   ├── wave-<index>.json
│   └── wave-<index>/
│       └── logs/
│           ├── <batch-id>.log
│           └── <batch-id>.usage.json
└── ...
```


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

Create the campaign branch and directory:

```bash
git -C <repo> checkout -b crustify/<target>-<model>
mkdir -p <repo>/crustify/campaigns/<target>
```

Wavefront does not create the parent directory for `schedule --output`.

## Required deps

CodeQL on macOS arm64 requires Rosetta.
Wavefront and ffibox are checkouts under the data prefix of the environment
crustify is installed in — `<prefix>/share/wavefront` and
`<prefix>/share/ffibox`. Crustify resolves them there itself; you configure no
paths. A checkout already present at either location is provisioned: do not
clone or reinstall it. `CRUSTIFY_DEP_WAVEFRONT` / `CRUSTIFY_DEP_FFIBOX`
override one of them for a checkout kept elsewhere.