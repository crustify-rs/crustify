<!-- INCLUDE specs/rust/conventions.md -->

---

<!-- INCLUDE specs/rust/toolchain.md -->

---

<!-- INCLUDE specs/rust/bindgen.md -->

---

<!-- INCLUDE specs/rust/items/binding.md -->

The tools serve it as follows:

<!-- INCLUDE specs/tools/wavefront/rust/items/binding.md -->
<!-- INCLUDE specs/tools/ffimap/rust/items/binding.md -->
<!-- INCLUDE specs/tools/ffibox/rust/items/binding.md -->

---

<!-- INCLUDE specs/rust/items/porting.md -->

The tools serve it as follows:

<!-- INCLUDE specs/tools/wavefront/rust/items/porting.md -->

---

<!-- INCLUDE specs/planning/decomposition.md -->

The tools serve it as follows:

<!-- INCLUDE specs/tools/wavefront/planning/decomposition.md -->

---

<!-- INCLUDE specs/planning/scheduling.md -->

The tools serve it as follows:

<!-- INCLUDE specs/tools/wavefront/planning/scheduling.md -->

---

<!-- INCLUDE specs/planning/dependencies.md -->

---

<!-- INCLUDE specs/workflows/binding.md -->

---

<!-- INCLUDE specs/workflows/porting.md -->

<!-- CAMPAIGN SPECS END -->

This is a port or wrap campaign: it translates a C codebase to Rust, binding each item
behind a safe Rust API or porting it to Rust, as `crustify/CRUSTIFY.md`'s `campaign`
answer selects.

### Agents

You spawn four kinds of agent, and each owns its part:

- planner agents own the plan: the module decomposition, the plan fields of the
  schedule, and the planning artifacts of the tools it uses;
- binder agents own the `wrap` batches, and translator agents the `port` batches;
- reviewer agents own the review batches.

Each owns the regression gates of its own work, and fills its own landing cells of the
dashboard.

You own everything else of the binding workflow above, and of the porting workflow in a
port campaign: the planner runs' branches, tasks, checks and promotion; the Rust tree's
scaffolding; the side campaigns of the out-of-tree libraries the plan needs, each a wrap
campaign you run in its own repository, as the dependencies spec describes; each module's `status`, which you set to `frozen` when the modules schema's Status
section times it; every module's branch and its integration into the working branch;
every wave, from its branch to its promotion; every batch, review batches included, from
its packing, branch and task to its landing; their progress in `schedule.json`; and the
accounting the Ownership section names.

### Brief

The campaign brief lists the modules, the out-of-tree libraries and whether each has a
wrapper on `crustify-rs` already, the assumptions you made, the backend, billing, model proxy and arguments of every agent, the review policy with its objectives, the sanitizers, and the execution policy:
whether modules run concurrently or their waves are merged, the batch, review and
parallelism caps if the settings set any, the ship points and the settings' approval
gates.

### Settings changes

The unit of work is the module, or the wave for a wave of no module. A changed `scope` or
`module-concurrency` answer re-plans the modules that are not frozen and the waves that
are `todo`: spawn planner runs as the binding workflow's Planning section describes,
under the new answers. A changed `campaign` answer, `wrap` to `port` or back, re-plans
under the new kind as the same section describes, the frozen modules' objectives
included. Landed work is never re-planned. A changed `workload` or
`review-workload` answer caps the batches you pack from the next unit of work on, and a
changed `ship` answer the points at which you ask to ship.

### Workflow

#### Phase 1: setup

1. **Setup.** Carry out the setup workflow's Provisioning, Repository, Artifact tree,
   Builds and Baseline sections.
2. **Planning.** Run the planner runs the binding workflow's Planning section describes,
   one after another. For each run `<n>`, create `crustify/planner/run-<n>` from the
   working branch's tip and check it out in the repository's base dir, write the run's
   `task.json` (see `specs/artifacts/task.md`) in its artifact dir, and spawn it:

   ```bash
   crustify spawn-planner <repo> crustify/artifacts/planner/run-<n>/task.json
   ```

   Once it has committed, check its diff against the plan's rules the Planning section
   gives, and report what breaks them rather than promote it. Otherwise promote it as the
   versioning spec's Lifecycle section describes, collect its records and fill its usage cells;
   start the next run only after that. After the last run, check that the plan is
   complete as the Planning section defines it. If the settings' `ship` answer is
   `decide after planning`, propose ship points from the plan now, as the binding
   workflow's Shipping section describes, and record the user's choice as the answer.
3. **Rust tree.** Scaffold the Rust tree as the binding workflow's Rust tree section
   describes, and commit it on the working branch.
4. **Side campaigns.** For each out-of-tree library the plan needs, as the planners'
   commits name them, put its `rust_equivalent` records and their notes to the user, with
   your recommendation, and record the user's choice as its `decision` in
   `dependencies.json`, as the dependencies spec's Wrappers section describes. For a
   library the user adopts a crate for, add the crate to the workspace and stop there. For
   each library the user chooses a wrapper for:
   - establish its wrapper as the dependencies spec's Wrappers and Reuse sections
     describe: clone `crustify-rs/<source>-crustify` beside `<repo>` when it exists, or
     initialize a new one there, with its `c/` as the Sources section describes, and
     create it on `crustify-rs` only once the user approves;
   - write its settings as the parent's, but for `campaign: wrap`, its source at the
     release the target links, and its scope, the entities the plan's dependency records
     count, and apply each settings change of the parent's to it as well;
   - carry out its setup workflow there, its builds installing the library once per
     variant of the parent, except for libc, which stays the system's; and
   - add it to the parent's workspace as a Git dependency pinned to its working branch's
     tip, recorded as its library's `wrapper.pin` in `dependencies.json`, with a Cargo `[patch]` to the clone, rebuild the parent's variants against its
     installs and run the parent's baseline again, as the setup workflow's Builds section
     describes.

#### Phase 2: translation

1. **Preflight.** Carry out the setup workflow's Preflight section.
2. **Waves and batches.** Run the waves the session covers, and their review batches, as
   the binding workflow's Order, Waves and batches, and Review batches sections describe,
   with the porting workflow's differences in a port campaign: prepare each wave as the
   versioning spec's Lifecycle section describes, pack its batches, write each task, spawn
   its agents as the concurrency spec describes, within the settings' `parallelism` when
   it sets one, record each batch's progress, and promote each wave once it completes.
   Create each home before its batch launches, as the Rust tree section describes.

   Pack each wave's batches when it starts, as the scheduling spec's Batches section
   describes: judge each batch's size from its items, the agent that runs it, how the
   campaign's batches have gone so far and the host, within the settings' caps, and share
   batches between consecutive waves where every dependency chain stays inside one. Before
   you launch a batch, check what its items depend on against what has landed, and bind
   what has not first, in a wrap batch of the same wave that lands before it, as the
   scheduling spec's Wrap batches section describes. When a batch fails, run it again or
   pack its items anew.

   When review is enabled, pack review batches as the batches they review land, larger
   than translation batches, as the reviewing spec's Review batches section describes, so
   that review runs beside the wave rather than after it, and mark the wave's last one,
   launched once every translation batch has landed, with `wave_gates`.

   With concurrent modules, start each module's run on its own branch as soon as the
   binding workflow's Order section allows, as many at once as the concurrency spec
   describes, and integrate each once its run's last wave has been promoted, one at a
   time, as the versioning spec's Integration section describes. No agent's gates cover
   the merge's tree, so you merge it, resolve its additive conflicts, and run its gates
   yourself; hand any other conflict, or a gate that fails, to an agent of the module's
   batch kind, with additional instructions to resolve it in the module's worktree.

   Before a wave whose items use entities of an out-of-tree library that its wrapper
   lacks, advance that library's side campaign, as the dependencies spec's Side campaigns
   section describes: spawn a planner run in its repository with additional instructions
   naming the entities the wave needs, run the waves that run plans, and promote them
   there; then move the parent's pin to the wrapper's working-branch tip, and its
   library's `wrapper.pin` in `dependencies.json` with it, in a commit on the parent's
   working branch, and start the wave.
3. **Shipping.** At each point the settings' `ship` answer names, once its modules have
   been integrated and passed their gates, ask the user whether to advance the shipping
   branch, as the binding workflow's Shipping section describes. A
   parent ships only once each wrapper it pins has shipped the commit it pins: ask for
   those wrappers' shipping too.
4. **Accounting.** Collect every run's records as soon as it lands or fails, and fill its
   usage cells, and each module's campaign cells, as the binding workflow's Accounting
   section times them. A side campaign's records and cells are its own, in its repository's
   dashboard; copy its figures into the parent's `Side campaigns` table each time the
   parent's pin moves, as the accounting spec's Side campaign cells section describes.

<!-- CAMPAIGN GUIDE START -->

- `workflows/binding.md` and `workflows/porting.md`: how a translation campaign proceeds,
  which your workflow above carries out.
- `planning/decomposition.md`, `planning/scheduling.md` and `planning/dependencies.md`: the
  plan the planner runs produce, which you check and promote.
- `rust/conventions.md`: follow it wherever it applies: when you scaffold crates, modules and
  test suites, and when you home each batch's items.
- `rust/toolchain.md`: follow it when you scaffold the workspace.
- `rust/bindgen.md`: follow it when you scaffold the raw bindings and when you publish the
  safe crate.
- `rust/items/binding.md` and `rust/items/porting.md`: how binders and translators do their
  work, for reference: use them to brief the user, to write additional instructions, and to
  judge what the agents report.
