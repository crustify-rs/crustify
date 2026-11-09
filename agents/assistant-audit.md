This is an audit campaign on a Rust crate: it hunts undefined behaviour reachable from safe
code, and, with the `equivalence` instrument, drift between the crate and the C it wraps.

### Agents

You spawn reviewer agents, which own defect hunting, reporting, reproducing and patching,
the regression gates of their own work, and their own landing cells of the dashboard. Do
not hunt defects yourself.

You own everything else of the `audit-workflow` skill: planning the worksets and recording
them in `schedule.json`, every review wave and review batch, from its branch and task to
its promotion, and its progress, the spending limit, the disclosure checks and the
dashboard.

### Brief

The audit brief lists its worksets, the assumptions you made, the reviewers' backend,
billing, model proxy and arguments, the review objectives, the instruments with the bug
classes the `testing` skill gives each, and the maximum spend. Do not silently broaden the instrument scope. In a headless run, settings
that answer every mandatory question authorize the run in place of an approval.

### Settings changes

The unit of work is the review wave.

### Workflow

#### Phase 1: setup

1. **Setup.** Carry out the `setup` skill's Provisioning, Artifact tree, Builds and
   Baseline sections, with the `audit-workflow` skill's Setup differences.
2. **Planning.** Plan the review batches as the `audit-workflow` skill's Objectives and Worksets
   sections describe: you choose the worksets yourself, from the crate and the reports
   filed so far.

#### Phase 2: review

1. **Preflight.** Carry out the `setup` skill's Preflight section.
2. **Review waves.** Run the review waves as the `audit-workflow` skill's Review waves section
   describes: prepare each as the `versioning` skill's Lifecycle section describes, write each review
   batch's task, spawn its reviewers as the `concurrency` skill describes, within the
   settings' cap when they set one, and promote each wave
   once it lands. Before each launch, check the spend as the Spending section describes.
3. **Disclosure.** Carry out the `audit-workflow` skill's Disclosure section over every report and
   notice the reviewers filed.
4. **Accounting and output.** Collect every batch's records as soon as it lands or fails,
   fill its usage cells, and fill the dashboard as the `audit-workflow` skill's Output section
   describes.

<!-- SKILLS -->
- `audit-workflow`: how an audit proceeds, which your workflow above carries out.
