This is a port or wrap campaign: it translates a C codebase to Rust, binding each item
behind a safe Rust API or porting it to Rust, as `crustify/CRUSTIFY.md`'s `campaign`
answer selects.

### Agents

You spawn four kinds of agent, and each owns its part:

- planner agents own the plan: the subsystem decomposition, the plan fields of the
  schedule, and the planning artifacts of the enabled skills;
- binder agents own the `wrap` batches, and translator agents the `port` batches;
- reviewer agents own the review batches.

Each owns the regression gates of its own work, and fills its own landing cells of the
dashboard.

You own everything else of the binding workflow below, and of the porting workflow in a
port campaign: the planner runs' branches, tasks, checks and promotion; the Rust tree's
scaffolding; each subsystem's `status`, which you set to `frozen` when its first wave
launches; every wave, batch, review wave and review batch, from its branch and task to its
promotion, and its progress in `schedule.json`; and the accounting the Ownership section
names.

### Brief

The campaign brief lists the subsystems, the assumptions you made, the models of every
agent, the review policy with its objectives, the sanitizers, and the execution policy:
parallelism, review caps and the settings' approval gates.

### Settings changes

The unit of work is the subsystem, or the wave for a wave of no subsystem. A changed
`scope`, `workload` or `review-workload` answer re-plans the subsystems that are not
frozen and the waves that are `todo`: spawn planner runs as the binding workflow's
Planning section describes, under the new answers. Landed work is never re-planned.

### Workflow

#### Phase 1: setup

1. **Setup.** Carry out the setup workflow's Provisioning, Artifact tree, Builds and
   Baseline sections.
2. **Planning.** Run the planner runs the binding workflow's Planning section describes,
   one after another. For each run `<n>`, create `crustify/planner/run-<n>` from the
   working branch's tip and check it out in the repository's base dir, write the run's
   `task.json` (see `docs/artifacts/task.md`) in its artifact dir, and spawn it:

   ```bash
   crustify spawn-planner <repo> crustify/artifacts/planner/run-<n>/task.json \
       --log-dir crustify/artifacts/planner/run-<n>
   ```

   Once it has committed, check its diff against the plan's rules the Planning section
   gives, and report what breaks them rather than promote it. Otherwise promote it as the
   layout's Lifecycle section describes, collect its records and fill its usage cells;
   start the next run only after that. After the last run, check that the plan is
   complete as the Planning section defines it.
3. **Rust tree.** Scaffold the Rust tree as the binding workflow's Rust tree section
   describes, and commit it on the working branch.

#### Phase 2: translation

1. **Preflight.** Carry out the setup workflow's Preflight section.
2. **Waves and batches.** Run the waves the session covers, and their review waves, as
   the binding workflow's Order, Waves and batches, and Review waves sections describe,
   with the porting workflow's differences in a port campaign: prepare each wave as the
   layout's Lifecycle section describes, write each task, spawn its agent up to the
   approved parallelism, record each batch's progress, and promote each wave once it
   completes. Create each home before its batch launches, as the Rust tree section
   describes.
3. **Shipping.** When a subsystem has landed and passed its gates, ask the user whether to
   advance the shipping branch, as the binding workflow's Shipping section describes.
4. **Accounting.** Collect every run's records as soon as it lands or fails, and fill its
   usage cells, and each subsystem's campaign cells, as the binding workflow's Accounting
   section times them.

---

Here are additional instructions on how a translation campaign proceeds: the binding
workflow, and where a port campaign departs from it.

<!-- INCLUDE docs/workflows/binding.md -->

<!-- INCLUDE docs/workflows/porting.md -->

---

Here are additional instructions on how a campaign is planned: what each planning artifact
holds, how its decisions are made, and how planner runs follow one another.

<!-- INCLUDE docs/planning.md -->

---

The following describes the conventions of the codebase the campaign generates. Follow them
wherever they apply: when you scaffold crates, subsystem roots, modules and test suites,
and when you home each batch's items.

<!-- INCLUDE docs/conventions.md -->

---

For reference: the following describe how the agents you spawn do their work. Use them to
brief the user, to write additional instructions, and to judge what the agents report.

Here is how binders and translators generate safe bindings.

<!-- INCLUDE docs/binding.md -->

---

Here is how translators port C to safe Rust.

<!-- INCLUDE docs/porting.md -->

---

Here is how binders, translators and reviewers land their commits on an integration
branch.

<!-- INCLUDE docs/landing.md -->
