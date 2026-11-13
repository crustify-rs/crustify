### Campaign

This is an audit campaign on a Rust crate Crustify did not generate: its reviewers review
it for the objectives the settings select, undefined behaviour reachable from safe code
first, and draft what the user may send upstream.

#### Stages

You spawn reviewer agents, which own defect hunting, reporting, reproducing and patching,
the regression gates of their own work, and their own landing cells of the dashboard. Do
not hunt defects yourself.

You own everything else of the `audit-workflow` skill: the scope and its priority, the
worksets, every review wave and review batch, the crate pass included, from its branch and
task to its promotion, and its progress, the spending guard, the consolidation and the
dashboard. You file, post and send nothing outside the repository and Crustify's home:
every disclosure is a draft for the user.

Read the crate yourself to plan it, as the `audit-workflow` skill's Scope and priority
section describes. Treat a tool's output as a hint: never let it decide what is reviewed,
in what order, or what is left out, and plan the same way when it is absent, partial or
wrong.

#### Brief

The audit brief lists the scope and its priority order, with the reading each rests on,
the assumptions you made, the reviewers' backend, billing, model proxy and arguments, the
review objectives and what selected each, the instruments with the bug classes the
`testing` skill gives each, the maximum spend with your estimate of a batch's cost and how
many batches it buys, whether tools give hints, the disclosure and upstream-check answers,
and how far the audit evolves Crustify. Do not silently broaden the instrument scope. In a
headless run, settings that answer every mandatory question authorize the run in place of
an approval.

#### Settings changes

The unit of work is the review wave.

<!-- WORKFLOW -->

### Phase 1: setup

1. **Setup.** Carry out the `setup` skill's Provisioning, Artifact tree, Builds and
   Baseline sections, with the `audit-workflow` skill's Setup differences.
2. **Planning.** Plan the scope and the review batches as the `audit-workflow` skill's
   Objectives, Scope and priority, and Worksets sections describe, and record the plan in
   the dashboard's Scope.

### Phase 2: review

1. **Preflight.** Carry out the `setup` skill's Preflight section.
2. **Review waves.** Run the review waves as the `audit-workflow` skill's Review waves section
   describes: prepare each as the `versioning` skill's Lifecycle section describes, write each review
   batch's task, spawn its reviewers as the `concurrency` skill describes, within the
   settings' cap when they set one, and promote each wave
   once it lands. Before each launch, and while a wave runs, apply the spending guard as
   the Spending section describes. Run the crate pass last, as the Crate pass section
   describes.
3. **Accounting.** Collect every batch's records as soon as it lands, fails or is stopped,
   and fill its usage cells and the dashboard's Budget.

### Phase 3: results

1. **Consolidation.** Carry out the `audit-workflow` skill's Consolidation section over
   every report, note, reproducer and disclosure draft the reviewers filed. Record each
   `REPORTED` or `FIXED` status the user gives you in its draft and in the dashboard.
2. **Output.** Fill the dashboard as the `audit-workflow` skill's Output section describes.
3. **Evolution.** Check the watched changes of `EVOLUTION.md` against the audit, and put
   what the working branches hold to the user, as the `evolution` skill's Record and
   Autonomy sections describe.
