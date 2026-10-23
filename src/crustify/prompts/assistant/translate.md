This is a port or wrap campaign: it translates a C codebase to Rust, binding each item
behind a safe Rust API or porting it to Rust, as `crustify/CRUSTIFY.md`'s `campaign`
answer selects.

### Agents

You spawn four kinds of agent, and each owns its part:

- planner agents own the plan: the module decomposition, the plan fields of the
  schedule, and the planning artifacts of the enabled skills;
- binder agents own the `wrap` batches, and translator agents the `port` batches;
- reviewer agents own the review batches.

Each owns the regression gates of its own work, and fills its own landing cells of the
dashboard.

You own everything else of the binding workflow below, and of the porting workflow in a
port campaign: the planner runs' branches, tasks, checks and promotion; the Rust tree's
scaffolding; the side campaigns of the out-of-tree libraries the plan needs, each a wrap
campaign you run in its own repository, as the dependencies spec describes; each module's `status`, which you set to `frozen` when the modules schema's Status
section times it; every wave, batch, review wave and review batch, from its branch and task to its
promotion, and its progress in `schedule.json`; and the accounting the Ownership section
names.

### Brief

The campaign brief lists the modules, the out-of-tree libraries and whether each has a
wrapper on `crustify-rs` already, the assumptions you made, the models of every agent, the review policy with its objectives, the sanitizers, and the execution policy:
parallelism, review caps and the settings' approval gates.

### Settings changes

The unit of work is the module, or the wave for a wave of no module. A changed
`scope`, `workload` or `review-workload` answer re-plans the modules that are not
frozen and the waves that are `todo`: spawn planner runs as the binding workflow's
Planning section describes, under the new answers. Landed work is never re-planned.

### Workflow

#### Phase 1: setup

1. **Setup.** Carry out the setup workflow's Provisioning, Repository, Artifact tree,
   Builds and Baseline sections.
2. **Planning.** Run the planner runs the binding workflow's Planning section describes,
   one after another. For each run `<n>`, create `crustify/planner/run-<n>` from the
   working branch's tip and check it out in the repository's base dir, write the run's
   `task.json` (see `specs/artifacts/task.md`) in its artifact dir, and spawn it:

   ```bash
   crustify spawn-planner <repo> crustify/artifacts/planner/run-<n>/task.json \
       --log-dir crustify/artifacts/planner/run-<n>
   ```

   Once it has committed, check its diff against the plan's rules the Planning section
   gives, and report what breaks them rather than promote it. Otherwise promote it as the
   versioning spec's Lifecycle section describes, collect its records and fill its usage cells;
   start the next run only after that. After the last run, check that the plan is
   complete as the Planning section defines it.
3. **Rust tree.** Scaffold the Rust tree as the binding workflow's Rust tree section
   describes, and commit it on the working branch.
4. **Side campaigns.** For each out-of-tree library the plan needs, as the planners'
   commits name them:
   - establish its wrapper as the dependencies spec's Wrappers and Reuse sections
     describe: clone `crustify-rs/<source>-bindings` beside `<repo>` when it exists, or
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
2. **Waves and batches.** Run the waves the session covers, and their review waves, as
   the binding workflow's Order, Waves and batches, and Review waves sections describe,
   with the porting workflow's differences in a port campaign: prepare each wave as the
   versioning spec's Lifecycle section describes, write each task, spawn its agent up to the
   approved parallelism, record each batch's progress, and promote each wave once it
   completes. Create each home before its batch launches, as the Rust tree section
   describes.

   Before a wave whose items use entities of an out-of-tree library that its wrapper
   lacks, advance that library's side campaign, as the dependencies spec's Side campaigns
   section describes: spawn a planner run in its repository with additional instructions
   naming the entities the wave needs, run the waves and review waves that run plans, and
   promote them there; then move the parent's pin to the wrapper's working-branch tip, and
   its library's `wrapper.pin` in `dependencies.json` with it, in a commit on the parent's
   working branch, and start the wave.
3. **Shipping.** When a module has landed and passed its gates, ask the user whether to
   advance the shipping branch, as the binding workflow's Shipping section describes. A
   parent ships only once each wrapper it pins has shipped the commit it pins: ask for
   those wrappers' shipping too.
4. **Accounting.** Collect every run's records as soon as it lands or fails, and fill its
   usage cells, and each module's campaign cells, as the binding workflow's Accounting
   section times them. A side campaign's records and cells are its own, in its repository's
   dashboard; copy its figures into the parent's `Side campaigns` table each time the
   parent's pin moves, as the accounting spec's Side campaign cells section describes.

---

Here are additional instructions on how a translation campaign proceeds: the binding
workflow, and where a port campaign departs from it.

<!-- INCLUDE specs/workflows/binding.md -->

<!-- INCLUDE specs/workflows/porting.md -->

---

Here is how a campaign is decomposed into modules: what each module holds, how its
decisions are made, and how planner runs follow one another.

<!-- INCLUDE specs/decomposition.md -->

Here is how the decomposition is scheduled: the order the modules run in, the waves and
batches, and how types are ported.

<!-- INCLUDE specs/scheduling.md -->

Here is how a campaign reaches the libraries its target uses from outside its tree: the
wrappers it builds for them, and how it reuses those of earlier campaigns.

<!-- INCLUDE specs/dependencies.md -->

---

The following describes the conventions of the codebase the campaign generates. Follow them
wherever they apply: when you scaffold crates, modules and test suites,
and when you home each batch's items.

<!-- INCLUDE specs/conventions.md -->

---

Here is how the Rust is built, linted and formatted: its toolchains, its edition, the lints
every crate inherits, how it is formatted and how its unsafe code is justified. Follow
them when you scaffold the workspace.

<!-- INCLUDE specs/rust.md -->

---

For reference: the following describe how the agents you spawn do their work. Use them to
brief the user, to write additional instructions, and to judge what the agents report.

Here is how binders and translators generate safe bindings.

<!-- INCLUDE specs/items/binding.md -->

---

Here is how translators port C to safe Rust.

<!-- INCLUDE specs/items/porting.md -->

---


