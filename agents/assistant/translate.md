### Campaign

This is a port or wrap campaign: it translates a C codebase to Rust, binding each item
behind a safe Rust API or porting it to Rust, as `crustify/CRUSTIFY.md`'s `campaign`
answer selects.

#### Stages

You spawn four kinds of agent: planners for the planner runs, binders for the `wrap`
batches, translators for the `port` batches and the later stages, and reviewers for the
review batches. Each owns its work, the regression gates of its work and its own landing
cells. Brief them, and judge what they report, by the skills their work follows:
`binding`, `binding-types`, `binding-symbols`, `porting`, `porting-types` and
`porting-symbols`, `testing` and `reviewing`.

You own every other part of the `binding-workflow` skill, and of the `porting-workflow`
skill in a port campaign: among them the Rust tree, the side campaigns, each module's
`status`, set to `frozen` when the `modules-schema` skill's Status section times it, every
module's branch and integration, and every wave and batch, review batches included, from
its packing to its promotion.

#### Brief

The campaign brief lists the modules, the out-of-tree libraries and whether each has a
wrapper on `crustify-rs` already, the assumptions you made, the backend, billing, model
proxy and arguments of every agent, the review policy with its objectives, the sanitizers,
and the execution policy: the batch, review and parallelism caps the settings set, the
ship points, the settings' approval gates and how far the campaign evolves Crustify.

#### Settings changes

The unit of work is the module, or the wave for a wave of no module. A changed `scope`,
`campaign`, `workload` or `review-workload` answer takes effect as the `binding-workflow`
skill's Planning section describes. Under a changed `campaign`, set every module's
`status` back to `todo` before the first planner run, and once the plan is promoted, move
each landed item whose home it changed, its code unchanged, in a commit on the working
branch before the next wave. A changed `ship` answer moves the points at which you ask to
ship.

<!-- WORKFLOW -->

### Phase 1: setup

1. **Setup.** Carry out the `setup` skill's Provisioning, Repository, Artifact tree,
   Builds and Baseline sections.
2. **Planning.** Run the planner runs the `binding-workflow` skill's Planning section
   describes, one at a time. Before you promote a run, check its diff against the plan's
   rules that section gives, and its decisions against the `decomposition`, `scheduling`
   and `dependencies` skills, and report what breaks them rather than promote it. Collect
   each run's records and fill its usage cells before the next starts. Once the plan is
   complete, if the settings' `ship` answer is `decide after planning`, propose ship
   points from it, as the `binding-workflow` skill's Shipping section describes, and
   record the user's choice as the answer.
3. **Rust tree.** Scaffold the Rust tree as the `binding-workflow` skill's Rust tree
   section describes, and commit it on the working branch.
4. **Side campaigns.** For each out-of-tree library the plan needs, put its
   `candidates`, its entities' recommended routes and its `recommendation` to the user,
   and record their choice as its `decision`, as the `dependencies` skill's Routes section describes. Add
   each adopted crate to the workspace, and clone each fork that extends one beside the
   campaign's repository, pinned with a Cargo `[patch]`, as that skill's Adopted crates
   section describes; open its upstream pull request only with the user's approval.
   Establish each wrapper the user chooses as that skill's Routes,
   Side campaigns, Sources and Reuse sections describe, creating it on `crustify-rs` only
   once the user approves; carry out its setup workflow in its repository, pin it in the
   parent's workspace, and rebuild the parent's variants and run its baseline again, as
   the `setup` skill's Builds section describes.

### Phase 2: translation

1. **Preflight.** Carry out the `setup` skill's Preflight section.
2. **Waves and batches.** Run the waves the session covers, and their review batches, as
   the `binding-workflow` skill's Order, Waves and batches, and Review batches sections
   describe, with the `porting-workflow` skill's differences in a port campaign, within the
   `parallelism` of the settings' `workload` answer when it sets one. Pack each wave's
   batches when it starts, as the `scheduling` skill's Batches and Wrap batches sections
   describe, judging their size
   from how the campaign's batches have gone so far. When a batch fails, run it again or
   pack its items anew. Once every other batch of the last wave of a module's `wrap` and
   `port` items has landed, run its module pass, as the `reviewing` skill's Review batches section describes, before you
   integrate the module.

   Before each wave starts, and when a batch reports an out-of-tree entity a wrapper
   lacks, advance that library's side campaign as the `dependencies` skill's Side
   campaigns section describes: spawn a planner run in its repository whose task message
   names the entities, run and promote the waves it plans there, and move the parent's pin
   in a commit on the parent's working branch.

   No agent's gates cover a module integration's merge, so you merge it, resolve its
   additive conflicts and run its gates yourself, as the `versioning` skill's Integration
   section describes, deleting a ported module's export feature and listing the C test
   cases nothing carries over; hand any other conflict, or a gate that fails, to an agent of the
   module's batch kind, whose task message asks it to resolve them in the module's
   worktree.
3. **Shipping.** At each point the settings' `ship` answer names, ask the user whether to
   advance the shipping branch, and the shipping branches of the wrappers it pins, as the
   `binding-workflow` skill's Shipping section describes.
4. **Accounting.** Collect every run's records, and fill the usage and campaign cells, as
   the `binding-workflow` skill's Accounting section times them, a side campaign's figures
   included, as the `accounting` skill's Side campaign cells section describes.
