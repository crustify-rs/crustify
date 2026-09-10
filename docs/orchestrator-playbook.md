# Orchestrator playbook

Driving crustify, in two phases. Setup: toolchain install through the first
commit of the initial Rust tree — authoring `build.json`, `cli-config.json` and
a campaign-wide `wavefront-config.json`, building the CodeQL database, extracting
the T1/T2 tables, emitting `subsystems.json`, and seeding crate shells.
Translation: preparing, running,
landing and scanning waves with `crustify-audit`. Read Setup
before any wave; every later stage reads what it produces.

Paths below are relative to the crustify checkout (`deps.crustify` in
`cli-config.json`). Run any command's `--help` for exact flags — argparse is the
source of truth.

## The artifact tiers

Three artifact tiers decide where a file goes.

| tier | path | authored | derived |
|---|---|---|---|
| repo | `<repo>/crustify/` | `build.json`, `crates.json`, `cli-config.json` | `subsystems.json`, `rust/` |
| Wavefront | `<repo>/crustify/wavefront/` | campaign-wide `wavefront-config.json`, `ownership-store.json` | `codeql/{db,t1,t2}/`, `.cache/` |
| campaign | `<repo>/crustify/campaigns/<target>/` | `<sub-campaign>/wavefront-config.json` | `<sub-campaign>/<wave-name>.json`, `<sub-campaign>/wave-<index>/logs/` |

Repo-tier describes the whole repository. Oracle targets describe C inventory;
campaigns contain one directory per sub-campaign, its tracked narrow oracle config and wave
plans, and wave-local execution logs. A repo can carry several
oracle targets and many named sub-campaigns.

Every repo-tier artifact contract has a commented example under `specs/` —
except `wavefront-config.json`, whose example lives in the standalone Wavefront
checkout's own `specs/`. Read the template before authoring or emitting an
artifact; detailed schema documents supplement the `_comment_*` keys.

### Campaign directory layout

Sub-campaign oracle configs, wave plans and wave execution logs live below the target
campaign directory:

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

`<target>` is the repo-relative translation target passed to the Crustify CLI, so a target
such as `ssl/statem` creates nested directories, while the repo-root target
uses `crustify/campaigns/` directly. The orchestrator numbers Wavefront's
recorded `waves` array from zero, creates
`crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/`, and passes that
directory to every translation and review batch invocation through `--output`.
The name follows the executable wave index, not a DAG layer: one wave may fold
several adjacent layers, whose range remains recorded in the schedule.

The harness generates a collision-resistant `<batch-id>` for each invocation
and redirects the agent stream to `<batch-id>.log`, with its accounting beside
it as `<batch-id>.usage.json`. Wave and batch inputs do not select the log
directory implicitly. Oracle configs and wave plans are tracked; wave execution
directories are gitignored.

## Phase 1 — Setup

From an untouched checkout to the first commit of the initial Rust tree.

### 1. Toolchains and checkouts

| need | install |
|---|---|
| Python ≥ 3.13 | system or `uv` |
| Claude Code CLI | `curl -fsSL https://claude.ai/install.sh \| bash` |
| OpenAI Codex CLI | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` |
| Rust | rustup: `cargo`, `clippy`; nightly with `rustc-dev` and `llvm-tools` |
| `bindgen-cli` | `cargo install bindgen-cli` |
| CodeQL | the CodeQL CLI bundle, on `PATH` |
| `ffibox` | `git clone https://github.com/crustify-rs/ffibox.git` |
| `wavefront` | clone beside `ffibox`; `python -m pip install -e <checkout>` |

On macOS arm64 the CodeQL bundle needs Rosetta.

**A provisioned environment has already done all of this.** When
`CRUSTIFY_DEP_CRUSTIFY` is set, the toolchains are installed, the three
checkouts are in place and the Python projects are installed editable — the
table above is already satisfied. Do not clone or reinstall any of it: a second
copy is not the one on `PATH`, and the paths the agents are handed below must
be the provisioned ones. Skip to step 2.

### 2. Bootstrap `crustify/`

```bash
mkdir -p <repo>/crustify
cp specs/gitignore <repo>/crustify/.gitignore
```

Author `<repo>/crustify/cli-config.json` from `specs/cli-config.json`:

| block | holds |
|---|---|
| `deps` | absolute capability paths: crustify and crustify-audit share the crustify checkout; wavefront and ffibox use their own |
| `bins` | absolute paths to `crustify`, `wavefront` and `crustify-audit` |
| `prompt_capabilities` | optional skill instructions injected per agent role |

**Absolute paths only.** An agent runs inside a git worktree, so nothing
relative to a cwd resolves the same way twice. The file is machine-local and
gitignored — it reaches a worktree through `worktree.link_shared`, not git.

**Take the paths from the environment when it offers them.** A provisioned
environment may export exactly these values.

For translators, list any of `wavefront`, `ffibox` and
`crustify-audit` under `prompt_capabilities.translator`. A missing capability
is omitted from the rendered prompt. This is an instruction ablation only: it
does not hide the checkout, executable, dependency or path from the agent.

### 3. `build.json`

Author from `specs/build.json`. It fixes the exact shell strings used from the
repo root for the campaign's three build stages: `configure`, `build`, and
`test`. Increment its `version` whenever any command changes; derived artifacts
record that version as provenance.

- Prefer a `configure` that disables deprecated features.
- Enable sanitizers, so agents catch memory-safety violations when testing their
  Rust against the C.
- Prefer parallel `build` commands; on a hybrid-core host, distribute over
  performance cores.

### 4. Build and baseline

Run `configure`, then `build`. Then run `test` to collect the port-equivalence
baseline, disabling any test that fails on the unported tree.

Record pass/total plus the name of every test disabled to reach that state in
the campaign record. A post-port run must match it. This is the only evidence
that a translation preserved behaviour, and it cannot be reconstructed later.

### 5. CodeQL database and the T1/T2 tables

Build the CodeQL database manually, and run
`wavefront <repo_root> extract-ql`
to emit the T1 (entities) and T2 (edges) against that database.

It writes one CSV per query under `crustify/wavefront/codeql/{t1,t2}/` — T1 entities, T2
edges. Every type/symbol record, the scope sets and the dependency DAG derive
from these on demand, which is why this is the one oracle command with side
effects and the only one that must be run explicitly. It takes minutes; re-run
it only after the C tree or the database changes.

### Prepare reusable C builds

Before spawning translators, the orchestrator prepares separate immutable,
out-of-tree C builds for the exact C revision, `build.json` version, compiler,
and instrumentation configuration:

- a plain build for the normal functional baseline;
- an ASan + UBSan build for every FFI and lifecycle test;
- a TSan build for the soundness module's race obligations. It cannot share the
  ASan build: the two runtimes are mutually exclusive, so the soundness workload
  is executed once per instrument rather than once in total;
- a BSan build where the BorrowSanitizer toolchain is available, for Tree
  Borrows aliasing across the Rust/foreign boundary; and
- a coverage build used only for campaign measurements.

Miri needs no C build — it cannot execute into the foreign library at all, so
its soundness obligations are limited to constructs that resolve on the Rust
side.

A wrap agent whose changes are limited to Rust, bindgen allowlists, or bindgen
input headers reuses the prepared sanitized build. An agent that changes
compiled C or a compiled shim must make and test a private replacement build;
the orchestrator refreshes the shared builds after that change lands. Reusing
the build never relaxes the sanitizer requirement for lifecycle tests.

After landing, the orchestrator runs the full sanitized regression
gate and measures the soundness-, equivalence- and unit-workload coverage
separately, once on each merged, reviewed wave for campaign accounting.
Each workload bounds a different obligation, so the three coverage figures are
reported apart and never summed.

### 6. Configure the campaign-wide oracle target

Author a campaign-wide `wavefront-config.json` under
`crustify/wavefront/` from
Wavefront's `specs/wavefront-config.json`.

This first target spans the user's campaign selection. If the user named target
subsystems, include those target implementation paths; if the user selected the
whole target, include all of its implementation paths; if the user asked you to
choose subsystems, include what you chose. This common target is
the inventory from which the orchestrator decomposes both the selected target
surface and its imported producer closure. More narrowly scheduled
sub-campaigns may be derived after decomposition.

It names **two file sets**. Entries in either set are a file
(`include/internal/statem.h`) or a directory with a trailing slash (`ssl/`),
which expands to every source and header beneath it. Naming a file the build
never compiled is harmless — T1 anchoring drops uncompiled candidates.

| key | what it names |
|---|---|
| `impl_files` | the sources — and private headers — that **implement** the library |
| `api_headers` | the headers that **publish** its API |

Both file sets are authored for every target. The oracle has no wrap/port
objective.

**Implementation graph.** `impl_files` + `api_headers`
together seed the `targeted` section. Classification is *definition-anchored*:
an entity is targeted iff its **body** lives in a named file (or, having no
body, all its declarations do). Name the implementations **and** the headers
that define the types — headers outside the target tree are never discovered
automatically, and a header-only list drops every function it merely
*declares*, whose body sits in a `.c` you did not name. Put a header in
`api_headers` only if its **implementors** are in `impl_files`; one whose types
are merely *used* reaches the imported section on its own.

**Public API graph.** Pass `schedule --api-headers-only`. It walks no bodies,
and only a struct **defined** in `api_headers` keeps its field layout. Forward
declarations stay opaque. API declarations seed the selection; `--transitive`
still includes their non-public signature dependencies.

Point `api_headers` at published headers (`include/openssl/`,
`include/libxml/`), never at a source tree.

**Three sets, two axes.** `targeted` / `imported` split on **ownership**;
`api` cuts **publication** across both, and is what a wrap campaign schedules:

| set | anchor | what it answers |
|---|---|---|
| `--targeted-only` | definition | the library this campaign owns |
| `--imported-only` | derived closure | its external dependencies |
| `--api-only` | **declaration** | what the headers publish |

They intersect rather than exclude, so `--api-only --imported-only` is the
re-export set. Layout still follows the definition site:

| | struct **defined** in a named file | only **declared** there |
|---|---|---|
| implementation graph | full field layout | opaque handle |
| `--api-headers-only` | full layout iff defined in `api_headers` | opaque handle |

So `--transitive` over an opaque-exported type pulls the type and nothing else.

The thin batch worklist's `objective` is the **verb** handed to its agent,
chosen per wave by the orchestrator. A target type in a port campaign might first
be wrapped and then ported, which is what the batch field exists for.

`out_of_scope.paths` refines what a directory entry expands to;
`out_of_scope.features` is documentation only.

Verify the result before proceeding:

```bash
wavefront <repo_root> --config <campaign-wavefront-config.json> \
  query files --targeted-only
wavefront <repo_root> --config <campaign-wavefront-config.json> \
  query files --imported-only
```

After the user picked a target, create the campaign's base branch and artifact
directory:

```bash
git -C <repo> checkout -b crustify/<target>-<model>
mkdir -p <repo>/crustify/campaigns/<target>
```

This scaffolding is orchestrator-owned. `wavefront schedule --output`
writes the requested wave file but fails if its parent directory does not
already exist.

### 7. Emit `subsystems.json`

After the campaign-wide oracle target is populated, emit
`crustify/subsystems.json` from `specs/subsystems.json`. Field semantics:
`docs/schemas/subsystems.md`.

Discover link units from the configured build's actual linker outputs. Store
link units and their subsystems as ordered lists; each list entry is identified
by its `name`. Cover exactly the target span the user selected and include its
complete imported producer closure.

Before assigning scope, decide whether each subsystem in the selected span
actually warrants a project-specific native Rust implementation. Do not mark
every selected C file `targeted` mechanically. Inspect the subsystem's purpose
and available Rust equivalents:

- Mark it `targeted` when its behavior or invariants are specific to the target
  project and should be translated into native Rust.
- Mark it `imported` when it is a universal collection, protocol, parser,
  algorithm, runtime utility, or similar facility for which the Rust standard
  library or a suitable existing Rust implementation should ultimately replace
  the C code. During a partial migration, retain that C implementation behind a
  wrapped FFI boundary so translated Rust remains interoperable with the rest
  of the C system; do not rewrite the generic implementation merely to make it
  native immediately.
- If a subsystem mixes project-specific behavior with replaceable generic
  machinery, split it so the project-specific portion can be `targeted` and
  the deliberate C boundary can be `imported`.

Verify that a proposed Rust equivalent actually matches the required
semantics, platform support, performance, and licensing before choosing this
boundary. Record the candidate equivalent and the reason for deferring native
migration in the campaign brief or status record. Thus `scope` records
translation intent: `imported` covers both oracle-discovered producer closure
and selected code deliberately retained as a C interoperability boundary.

Home every covered translation unit to exactly one subsystem. Keep a subsystem
scope-homogeneous: do not mix targeted and imported translation units. Use the
wavefront oracle's LoC, type, symbol, and edge statistics whenever available. Aggregate
each consumer-to-producer relationship into one `depends_on` record with
`nr_edges`.

The resulting subsystem graph must be acyclic. Resolve a cycle by changing the
decomposition—rehome translation units or merge subsystems—rather than omitting
real dependency records. A subsystem with more incoming consumer edges has
greater producer weight and should preferentially remain a producer;
`nr_edges` refines that judgment.

This is orchestrator judgment, not a new mechanical validation command or
gate.

### 8. Seed crate shells

Author `crustify/crates.json`, the placement oracle. Schema:
`docs/schemas/crates.md`; example: `specs/crates.json`.

Seed the campaign's target crate and the top-level crates that own its imported
dependencies. Leave `modules` empty and do not home items yet. Crate names
match `subsystems.json`'s `link_units[*].name`; derive their dependency
relationships from subsystem `depends_on` records.

The orchestrator creates minimal compiling wrapper crates. Each starts with a
`Cargo.toml` and empty crate root following `conventions.md`. Do not create
campaign modules yet.

For each target or imported library crate, create its `<lib>-sys` placeholder:
`Cargo.toml`, `src/lib.rs`, `build.rs` and the bindgen input. Its bindgen
pipeline must compile with an empty, no-match agent-owned allowlist. Translator
agents populate that allowlist lazily.

Gate the shells:

```bash
crustify <repo_root> <target> crates validate
cargo build
cargo test
```

### 9. Commit

Commit the initial `rust/` tree on `crustify/<target>-<model>`. Translate waves
branch from this baseline.

### Gates before the first wave

| check | how |
|---|---|
| baseline recorded | campaign record names pass/total and every disabled test |
| T1/T2 populated | `crustify/wavefront/codeql/{t1,t2}/` non-empty |
| scope is what you meant | `query files --targeted-only` / `--imported-only` |
| placement consistent | `crates validate` exits clean |
| FFI crates link | `cargo build` + `cargo test` on each `<lib>-sys` |
| DAG resolves | `query dag --layer 0` returns the leaf set |

---

## Phase 2 — Translation

A sub-campaign is the translation of exactly one subsystem from
`subsystems.json`. Its objective-neutral scheduler-produced JSON document
composes that subsystem with its imported producer closure, divides the result
into sequential waves and packs each wave into batches. The
orchestrator, not a schedule-wide CLI process, enforces wave barriers and
promotion. It invokes one CLI process per recorded batch; that process creates
one isolated agent worktree and runs one agent.
See `docs/schemas/wave.md` for the producer/consumer contract.

### Plan sub-campaigns

For a wrap campaign, derive the workset from published declarations by passing
`--api-headers-only` to every ordinary `wavefront schedule` invocation. Do not
substitute the implementation graph: it includes private implementation units
that are outside a safe-wrapper campaign's target surface. `--transitive` is
still optional and means “include signature dependencies”; it does not change
the requirement to use the public API graph.

Every ordinary sub-campaign maps one-to-one to a subsystem.
A large subsystem is controlled by wave and batch barriers.
Raw-lifetime discovery is the only synthetic sub-campaign.

Run one `wavefront schedule` composition for that subsystem. The emitted plan
is authoritative for its imported producer closure, dependency barriers and
batch boundaries. Wavefront remains objective-neutral: `--api-headers-only`
selects the public-signature graph for a wrap campaign, while the orchestrator
supplies the execution objective separately according to the campaign and
subsystem policy below. The orchestrator does not estimate a closure from
directory names, create an ad-hoc combined sub-campaign, or reinterpret the
recorded waves and batches.

Execute subsystem sub-campaigns bottom-up over the composed dependency graph.
A consumer wave cannot start until every producer wave it depends on has
passed adversarial review and promotion. When several subsystem roots are
ready, use deterministic `(link_unit, subsystem)` ordering; producer weight is
only a tie-breaker. Sub-campaign size has no separate unit budget or default.
Its natural size is the completed-item-filtered subsystem closure; batch caps
bound each agent's worklist.

Before scheduling a narrower sub-campaign, author
`crustify/campaigns/<target>/<sub-campaign>/wavefront-config.json` from
Wavefront's spec. Its `impl_files` and `api_headers` must be exact subsets of
the campaign-wide config and must name that sub-campaign's implementation and
published API surface. Wavefront derives the imported closure directly from
this config; do not estimate a closure from directory names or from
`subsystems.json` statistics. Use the campaign-wide config for a sub-campaign
only when its intended scope really is campaign-wide, such as raw-lifetime
discovery.

### Preflight and monitor agentic stages

Before spawning any translation, review, or audit agent, resolve the selected
model to its provider and backend, then verify the backend executable is on the
stage process's actual `PATH` and responds to `--version`. Verify the required
credential variable is present without printing it, and reject an unsupported
provider/billing combination before creating worktrees. Run the stage's dry
run and confirm its unit, wave, and batch counts match the approved schedule.

Treat launch as successful only after every expected batch process for the
current wave is live, its log exists, and its backend has emitted its model
handshake or first repository action. An immediate backend, authentication, or
model-routing error is a failed launch: stop the wave, repair the environment,
and restart the unchanged batch set rather than allowing consumers to run.

Attach a persistent completion monitor to every running batch process. Poll or
await it independently of user status requests, and notify the user promptly
when it completes or fails. On process exit, verify the exit status, expected
log and usage record, landed commit and worktree state before
declaring the batch complete. A detached process without an attached completion
monitor is not an active campaign stage.

### Prepare each wave

Before executing a sub-campaign, the orchestrator:

1. verifies that the reusable C builds still match the current C revision and
   build provenance;
2. runs `wavefront schedule --config` with the sub-campaign's narrow config,
   selection and batch budgets, writing
   `crustify/campaigns/<target>/<sub-campaign>/<wave-name>.json`;
3. verifies the plan provenance, summary counts, wave barriers and batch
   identities;
4. homes its items in `crates.json`, creates their `.rs` files and connects
   them to the crate root before any batch in the sub-campaign starts;
5. runs `crates validate` and compiles the affected crates;
6. records the canonical tip as the immutable base of wave 0.

For each recorded wave, the orchestrator creates one integration branch at the
wave-base commit, leaves it unchecked out, and creates the output directory
passed to every batch harness:

```text
crustify/wave/<target-slug>/<sub-campaign>/wave-<index>
crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs/
```

The branch is the wave transaction and the sole landing target. It must remain
unchecked out so translators can update it with Git's atomic fast-forward
check. For each recorded batch, the orchestrator mechanically projects a thin
JSON worklist containing the execution `objective` and each item's `name`,
`defined_in`, `kind` and `field_anchors`; it performs no semantic rescheduling
while doing so. The harness derives the agent route from the homogeneous item
kinds. The orchestrator invokes one CLI process per worklist, concurrently up
to the approved parallelism. The harness generates a unique batch id and
creates one branch plus one worktree from the branch passed through
`--base-branch`:

```text
crustify/batch/<batch-id>
```

The harness only creates and prepares the worktree, links the shared ignored
campaign state, starts the backend and redirects its stream. The translator
commits, atomically lands onto the wave branch with rebase-and-retry on a
rejected fast-forward, and prunes its own worktree after landing. A failed
translator retains its branch and worktree for inspection. There is no session
branch or session worktree.

The projected batch schema is deliberately thin and strict:

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

Kinds are `type`, `symbol`, `callback`, and `raw-lifetime`. Type items route to
the type agent; symbols and callbacks share the symbol route. A raw-lifetime
batch contains exactly one `void` or `string` marker with `defined_in: null`.
Every other item carries a non-empty definition path. `field_anchors` is always
present and is non-empty only for a type. Do not add route, wave, batch, branch,
log or dependency fields: the harness derives the route, receives the base and
output paths as CLI flags, and the translator queries semantic context by item
identity.

```bash
wavefront <repo_root> \
  --config <repo>/crustify/campaigns/<target>/<sub-campaign>/wavefront-config.json \
  schedule \
  --output <repo>/crustify/campaigns/<target>/<sub-campaign>/<wave-name>.json \
  --name <items...> [--transitive] [--api-headers-only] \
  [--max-syms N] [--max-loc N] [--max-types N] [--min-fields N]
crustify <repo_root> <target> translate \
  <batch.json> \
  --base-branch crustify/wave/<target-slug>/<sub-campaign>/wave-<index> \
  --output <repo>/crustify/campaigns/<target>/<sub-campaign>/wave-<index>/logs \
  --dry-run
```

The orchestrator monitors every process and verifies from its exit status, log,
usage record and the wave branch that every batch landed. Landing contention is
owned by the translator's existing atomic fast-forward/rebase loop; it is not
permission to discard either change or for the orchestrator to translate a
worklist itself.

After translation batches land, run the adversarial review stage over the
merged wave before any consumer wave starts. By default, review batches reuse
the same item projections with `objective` changed to `review`, fork from the
merged translation tip and land through the same wave-branch flow.
Run the deterministic audit and regression gates on the translation-plus-review
tip. Promote that tip to the canonical campaign branch; it becomes the next
wave's immutable base.

The batch command inserts TODO anchors. Translator agents extend their
worklist's bindgen allowlists and regenerate bindings in their worktrees.

Do not change `crates.json` during a wave. When landing parallel agents, union
their `<lib>-sys` allowlist changes and rerun the affected crate tests.

### Execution objectives

A **wrap** campaign sets every thin batch worklist's `objective` to `wrap`. Its
schedules always use `wavefront schedule --api-headers-only`; this selection
rule is independent of the execution objective supplied to `crustify
translate`.

A **port** campaign distinguishes the user-selected migration set from its
dependency closure. A selected type runs `wrap` when it is scheduled for the
first time, so it stays layout-compatible while C still reads its fields, and
runs `port` once those C-side readers are gone. A selected symbol runs `port`
directly. `port` re-visits a filled anchor deliberately, so it is how an item is
escalated rather than redone, and it is what starts the opacification burn-down.

When the user chooses to migrate only a subset of the targeted closure, the
remaining dependencies run with `wrap` and form the deliberate C/Rust boundary.
This applies to symbols as well as types: a wrapped dependency keeps its C
implementation and exposes a safe Rust surface to selected ported items.
Schedule and complete those producer subsystems before invoking selected
migration batches with `port`; Wavefront remains objective-neutral. If the user
chooses the whole targeted closure instead, targeted symbols run with `port`
directly.

Do not include completed items when authoring the next oracle schedule.

### Raw lifetime discovery sub-campaigns

Regardless of the target set, the first two sub-campaigns are raw lifetime
discovery. They produce release/clone strategies for owned pointers that host
type-erased and NUL-terminated objects. Generate the `raw-lifetime-void` waves
with `schedule --lifetime-for void`, complete and adversarially review every
wave, then do the same for `raw-lifetime-string` with
`schedule --lifetime-for string`. When resuming an interrupted campaign, skip
either sub-campaign only if it has already completed.

### Land and promote

After a wave's translation and adversarial-review commits land on its
integration branch, check every batch exit status, log and usage record, then
make sure the C and Rust targets build and the tests pass. No need to check the C build/tests
for a wrap wave whose C side did not change.

Run the deterministic scan over the merged wave, seeding the exact C type and
symbol names scheduled in it:

```bash
crustify-audit <repo_root> unsafe --name <wave names...> --json
```

Inspect each entry's source-site lists. A site is a lead, not a failure: fix a
wrapper bypass or unsound reference, and leave a necessary FFI seam in place
with its safety justification.

`crustify/audit/unsafe.json` is reproducible and gitignored. The
orchestrator's post-merge scan is the wave record.

After verifying everything is green, promote the reviewed wave integration
branch to the canonical branch. A consumer wave always forks from that promoted
tip.

At the end of the campaign, record one unseeded tree-wide scan:

```bash
crustify-audit <repo_root> unsafe --json
```

### Adversarial review objective

Every translated wave has a mandatory `review` stage after all of its
translation batches land and before its first consumer wave starts. Reviewers
inspect the merged wave, actively seek counterexamples to its ownership,
lifetime, thread-safety, error-mapping and C-equivalence claims, and implement
focused fixes and regressions on isolated review branches. A translation wave
cannot promote on review findings alone: the fixes must land and all gates must
pass.

Use the backend and model the user selected, or orchestrator's choice when they
delegated it. This agentic review is independent of the deterministic
`crustify-audit unsafe` gate above. Use the translation batch caps for review
by default and reuse the translated wave's item projection with each thin
batch's `objective` set to `review`. When the campaign
has distinct review caps, have Wavefront re-batch the exact item identities in
that translated wave without expanding their closure; execute any review waves
it emits in order. The orchestrator does not regroup them itself, and no
consumer starts until the whole review schedule lands and passes its gates.
Do not repeat a generic end-of-sub-campaign review: the wave gates have already
reviewed every change before its consumers ran. Add an integrative sub-campaign
review only when the target's cross-wave behavior gives it a distinct, named
obligation.

### UB patch promotion

Run `crustify-audit ub` only with the user's explicit approval. The UB agent
should normally run once at the end of the whole campaign, after all
sub-campaigns and their allowed review passes have landed. Run it earlier only
when the user explicitly requests another milestone or a confirmed finding
blocks further work. The UB agent
owns both the evidence and the repair: it creates a dedicated branch in the
target repository, follows that repository's conventions, implements focused
regression tests, builds the affected targets, runs their gates, reruns the
reproduction, and commits the patch without merging it. The orchestrator does
not rewrite that patch. Inspect its diff and evidence, independently rerun the
relevant build, test, and reproduction gates, and merge the agent branch into
the canonical campaign branch only when they are green and the change is
confined to the confirmed finding. Otherwise leave it unpromoted and report the
specific failure.

### Accounting

Use `crustify-log-cost` over the per-agent `<batch-id>.usage.json` to compute cost
and fetch token usage, and never from provider-reported dollars.
The orchestrator records wave wall time from first batch launch through the
final review and regression gate. Fetch each agent wall from its
`<batch-id>.usage.json`.

Fill whatever evaluation table the user provides.

---

## Self-repair

If throughout driving campaigns you discover any bugs or flaws in `crustify`,
`wavefront`, `crustify-audit`, or `ffibox`, including new generic primitives that can be used
for C/Rust interop in `ffibox`, then create a new branch and worktree on the respective repository,
naming it accordingly, and develop a patch for the fix / enhancement.
