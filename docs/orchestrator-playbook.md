# Orchestrator playbook

The orchestrator sets up the campaign, schedules batches, monitors agents,
lands and reviews waves, runs regression gates, promotes verified tips, and
records results. Translators implement their assigned worklists.

Paths are relative to the Crustify checkout in `deps.crustify`. Read each
artifact's example under `specs/` and its schema before creating it. Use live
`--help` output for command flags and defaults.

## Required campaign decisions

Record these before changing the campaign repository:

- source repository and revision;
- `wrap` or `port` objective;
- target subsystems, functions, types, or whole repository;
- translation backend and model;
- review backend and model, or no agentic review;
- optional UB-audit backend and model;
- API or subscription billing;
- batch caps and parallelism;
- review batch caps;
- autonomous execution or explicit approval gates; and
- results file and format.

If the user delegates scope, prefer code with manual memory management or
untrusted-input parsing. If execution is not autonomous, record separate gates
for setup, translation, sub-campaign transitions, review, and UB audit. Present
one campaign brief and obtain approval before setup. Do not ask the user to
approve individual waves unless requested.

## Artifacts

- `crustify/.gitignore` — excludes machine-local configuration, caches, builds,
  logs, and generated analysis output.
- `crustify/build.json` — records the versioned configure, build, and test
  commands.
- `crustify/cli-config.json` — records machine-local dependency and executable
  paths plus prompt capabilities; ignored and linked into worktrees.
- `crustify/crates.json` — assigns translated items and modules to Rust crates.
- `crustify/subsystems.json` — records link units, subsystem scope, and the
  subsystem dependency graph.
- `crustify/wavefront/wavefront-config.json` — defines the campaign-wide source
  inventory.
- `crustify/wavefront/ownership-store.json` — stores authored semantic findings.
- `crustify/wavefront/codeql/t1/*.csv` — contains extracted entity records.
- `crustify/wavefront/codeql/t2/*.csv` — contains extracted dependency edges.
- `crustify/campaigns/<target>/<sub-campaign>/wavefront-config.json` — narrows
  source inventory to one sub-campaign.
- `crustify/campaigns/<target>/<sub-campaign>/<wave-name>.json` — records the
  generated wave and batch plan.
- `crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/<batch-id>.log`
  — contains one agent's output stream.
- `crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/<batch-id>.usage.json`
  — contains one agent's token, cost, and wall-time record.

Read the corresponding example and schema before creating an artifact. Track
authored configs and wave plans. Ignore machine-local config, extracted data,
caches, build outputs, and execution logs as specified by `crustify/.gitignore`.

## Directory structure

```text
crustify/campaigns/<target>/
├── raw-lifetime-void/
│   ├── wavefront-config.json
│   └── <wave-name>.json
├── raw-lifetime-string/
│   ├── wavefront-config.json
│   └── <wave-name>.json
├── <sub-campaign>/
│   ├── wavefront-config.json
│   ├── <wave-name>.json
│   └── wave-<index>/
│       └── logs/
│           ├── <batch-id>.log
│           └── <batch-id>.usage.json
└── ...
```

`<target>` is the repository-relative CLI target. A root target uses
`crustify/campaigns/`; `ssl/statem` uses
`crustify/campaigns/ssl/statem/`.

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
- CodeQL CLI;
- supported agent backends;
- Crustify and `crustify-audit`;
- Wavefront; and
- ffibox.

CodeQL on macOS arm64 requires Rosetta.

If `CRUSTIFY_DEP_CRUSTIFY` is set, use the provisioned toolchains and checkout
paths. Do not clone or reinstall them.

### 2. Bootstrap `crustify/`

```bash
mkdir -p <repo>/crustify
cp specs/gitignore <repo>/crustify/.gitignore
```

Create `crustify/cli-config.json` from `specs/cli-config.json`:

- `deps`: absolute checkout paths;
- `bins`: absolute executable paths; and
- `prompt_capabilities`: optional role-specific skill instructions.

Use absolute paths because agents run in isolated worktrees. The file is
machine-local and reaches worktrees through `worktree.link_shared`.

Translator capabilities may include `wavefront`, `ffibox`, and
`crustify-audit`. Omitting a capability removes its prompt instructions only;
it does not hide the executable, checkout, or path.

### 3. Create `build.json` and record the baseline

Create `crustify/build.json` from `specs/build.json`. Store the exact
repository-root commands for `configure`, `build`, and `test`. Increment
`version` whenever any command changes.

- Disable deprecated features when practical.
- Enable campaign sanitizers.
- Use parallel builds.

Run `configure`, `build`, and `test` against the unmodified source revision.
Disable unstable baseline tests as needed. Record pass/total and every disabled
test in the campaign results. Post-port results must match this baseline.

### 4. Extract CodeQL data

Build the CodeQL database, then run:

```bash
wavefront <repo_root> extract-ql
```

This creates T1 entity CSVs and T2 edge CSVs under
`crustify/wavefront/codeql/{t1,t2}/`. Re-run only when the C source or CodeQL
database changes.

### 5. Prepare reusable C builds

Create immutable out-of-tree builds for the exact C revision, `build.json`
version, compiler, and instrumentation, so that translator agents can reuse
them:

- plain build for the functional baseline;
- ASan + UBSan build for FFI and lifecycle tests;
- TSan build for race tests; do not combine it with ASan;
- BSan build when BorrowSanitizer is available; and
- coverage build for campaign measurements.

Miri does not need a C build and cannot call the foreign library.

A Rust-only change, bindgen allowlist change, or bindgen input-header change may
reuse a matching build. A change to compiled C or a compiled shim requires a
private build; refresh shared builds after that change lands.

After each reviewed wave, run the sanitized regression gate. Measure
UB, equivalence, and unit coverage separately; do not sum them.

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

### 7. Create `subsystems.json`

Create `crustify/subsystems.json` from `specs/subsystems.json`; see
`docs/schemas/subsystems.md`.

Use actual linker outputs to identify link units. Cover the selected target and
its complete imported producer closure. Assign every translation unit to one
subsystem. Keep each subsystem entirely `targeted` or entirely `imported`.

Use these scope rules:

- `targeted`: project-specific behaviour or invariants to implement in Rust;
- `imported`: generic facilities retained behind a wrapped C boundary; and
- split mixed subsystems so project-specific code and generic facilities have
  separate scopes.

Before marking a generic facility imported, verify the proposed Rust
replacement's semantics, platform support, performance, and licensing. Record
the replacement and reason for deferral.

Aggregate each consumer-to-producer relation into one `depends_on` record with
`nr_edges`. The subsystem graph must be acyclic. Resolve cycles by rehoming
translation units or merging subsystems; never remove a real dependency edge.
Prefer the side with higher incoming producer weight when selecting a boundary.

### 8. Create crate shells

Create `crustify/crates.json` from `specs/crates.json`; see
`docs/schemas/crates.md`.

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
- Record the link units owned by each crate. Derive `depends_on` only from
  subsystem edges that cross crate boundaries; internal edges stay between
  modules in the target crate.
- Leave `modules` empty; do not home items yet.
- Create minimal `Cargo.toml` and crate roots using `conventions.md`.
- Each `-sys` crate needs `Cargo.toml`, `src/lib.rs`, `build.rs`, and bindgen
  input.
- Its agent-owned allowlist must compile while empty.

Run:

```bash
crustify <repo_root> <target> crates validate
cargo build
cargo test
```

Commit the initial Rust tree on `crustify/<target>-<model>`.

### Setup gate

Before the first wave, verify:

- baseline pass/total and disabled tests are recorded;
- T1 and T2 directories are populated;
- targeted and imported file queries match the approved scope;
- `crates validate` passes;
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
4. home all scheduled items in `crates.json`;
5. create and connect their `.rs` modules;
6. run `crates validate` and compile affected crates; and
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

Do not edit `crates.json` during a wave. After parallel landings, union
conflicting `-sys` allowlist additions and retest the affected crates.

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
crustify-audit <repo_root> unsafe --name <wave names...> --json
```

Inspect each source site. Fix unsafe wrapper bypasses and unsound references.
Keep necessary FFI seams with a safety justification. The generated
`crustify/audit/unsafe.json` is ignored.

Do not run a generic end-of-sub-campaign review after every wave has already
been reviewed. Add one only for a named cross-wave obligation.

At campaign end, record an unseeded scan:

```bash
crustify-audit <repo_root> unsafe --json
```

### 7. Optional UB audit

Run `crustify-audit ub` only with explicit user approval. Run it once after the
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

Run `crustify-log-cost` over `<batch-id>.usage.json` files. Use its computed
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

When a campaign exposes a defect in Crustify, Wavefront, `crustify-audit`, or
ffibox, create a dedicated branch and worktree in that component's repository.
Implement and validate the reusable fix there; do not mix it into campaign
translation commits.
