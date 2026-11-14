---
name: evolution
description: "How Crustify repairs and improves itself from what its campaigns expose: goals, signals, proposals, lessons, evolution branches, validation, review, autonomy, adoption, and where the record of what landed is kept. Read before filing a defect in Crustify or a tool, proposing or making a change to either, or recording a campaign's lesson; `evolution-record` holds the record and how evolution itself evolves."
---

# Evolution

How a campaign changes the harness that runs it, Crustify's skills, agents, templates and
providers, its tools and the tools it lacks, and how its agents propose changes to the
campaign's artifacts that other roles own. A campaign exposes what the harness gets
wrong, what it constrains needlessly and what it repeats by hand; evolution turns that
evidence into changes, under the autonomy the settings' `evolution` answer grants, and
this guidance itself among them. Where a change goes within Crustify is
[`authoring`](../authoring/SKILL.md)'s.

## 1. Goals

Every change is judged against Crustify's goals, [`GOALS.md`](../../../GOALS.md), read in
full before the first proposal: a change serves one of them, or it is not made. The goals
are evolved too, when the evidence questions them, as `GOALS.md` describes.

A change to a tool is judged against that tool's own goals and non-goals too, the document
its tool skill names, read in full before the first change to the tool: they keep what the
tool is from drifting, such as an analysis that stays syntactic and does no data-flow
analysis. A change that departs from one of them is proposed, not made, and says so. A
tool with no such document has every change that alters what it is, rather than fixing or
extending what it does, proposed, not made.
<!-- TODO: ffimap has no goals document yet. -->

## 2. Signals

Evolution starts from evidence a campaign produces, never from taste:

| signal | what it suggests |
|---|---|
| a tool that crashes, or reports what the source contradicts | a defect in the tool |
| skills that contradict each other, or an agent prompt that leads its agent wrong | a defect in the spec |
| a rule an agent works around, or that forces a worse result than its omission would | an overconstraining rule, loosened or removed |
| review findings that recur across batches, in one objective or category | a rule the how-to skills lack |
| failed or rerun batches, and plan corrections | a defect in planning, scheduling or packing |
| the user's corrections | a rule, or a lesson of the campaign |
| cost or time outliers, in the dashboard | waste in batch sizing, gates or tooling |
| one representation hand-written in several places, or a TODO met again and again | a primitive or tool feature that is missing |
| one procedure repeated by hand: the same script written again, the same queries run in sequence | a tool, or a subcommand of one |
| a signal evolution missed, or a proposal that proved wrong | a defect in this guidance |
| a goal no decision cites, two that keep conflicting the same way, or a well-founded change no goal serves | a change to the goals |

A proposal needs one of these, with its evidence: a defect, a failure, a recurring
finding, a workaround or a measured waste. Fewer, well-founded proposals serve better than
many small ones: a change made for style alone, or for completeness, or to have proposed
something, is not made.

## 3. Destinations

Each signal goes to one destination:

- **the campaign alone**: what a setting or a task message settles, which changes nothing
  of Crustify;
- **a lesson**: a rule that holds for this target alone, recorded in the campaign's
  [`LESSONS.md`](#5-lessons);
- **the spec**: a skill, an agent, a template or a provider, where `authoring` places it;
- **a tool**: its code, its documentation or its tests, or a new tool; or
- **a campaign artifact**: the plan, the dependencies, the schedule or the dashboard, where
  the evidence shows one wrong or improvable and another role owns it. Its owner applies
  the proposal or declines it, a plan's at the next planner run.

A rule an agent cannot follow because its host refuses it, a write or a tool call
blocked, or a launch mode that withholds what the role needs, is a defect of that host's
provider, not of the rule: the provider prevents it with whatever its host offers, its
agents' definitions, the settings and permissions it installs, its hooks, the mode it
launches runs in, or the host's memory, and the spec is not bent around one host. Until
the provider's change lands, a run that meets the refusal neither works around it nor drops
what it could not do: it hands that to the assistant, in its final message, and the
assistant carries it out.

The test between a lesson and the spec is generality: a rule that can only be stated in
the target's own names is a lesson, and one the spec takes is stated without them, as it
would hold for any C codebase.

## 4. Proposals

A proposal is filed in the campaign's repository under `crustify/evolution/<slug>/`, as its
`PROPOSAL.md`. It states:

- the signal and its evidence, with the runs, findings and commits it cites;
- the goal it serves, by name, and the fitness measure of that goal it expects to move;
- its destination;
- the change, or the patch;
- how it was validated;
- the row the record takes when the change lands, as [`evolution-record`](record/SKILL.md) describes;
- its review's verdict; and
- its status: `open`; `deferred`, with what it waits for; `landed`, with the commit it
  landed as; `declined`, with why; or `superseded`, with the proposal that replaces it.

The campaign keeps an index of its proposals, `crustify/evolution/INDEX.md`, one row per
proposal: its slug, its signal in a line, its status, the runs that met the signal, and the
row of the record it matches, if any. The index has one writer per campaign, so that two
runs never write a row at once. It is written as each batch's proposals land, and holds
every proposal of the campaign before a wave launches.

A signal is filed once. Before a run files a proposal, it reads the index, in its worktree,
and the record, in Crustify's checkout. Where neither holds its signal, it files the
proposal. Where one does, it files nothing new:

- when the proposal the index names is in the run's own repository, the run adds its
  evidence to that proposal, as an occurrence;
- otherwise, the run reports the occurrence in its final message, and the index's writer
  records it.

A lesson is not filed as a proposal: `LESSONS.md` records it. A defect in a tool found
while reviewing is a proposal, not a finding on the reviewed code, and is filed with its
reproducer.

## 5. Lessons

The campaign's lessons sit in `crustify/LESSONS.md`, read by every run of the campaign
before its first step. Each lesson is one entry, under a heading that is its id: a short
slug no other lesson of the file has. An entry holds a status, one rule, the evidence the
rule rests on, and, on a line of its own, its scope: the modules, items or stages it holds
for.

A lesson steers every later run, as a rule of the spec does, so it is reviewed:

- A new or changed lesson is `provisional`. The first review batch whose worklist holds the
  commit that added or changed it reads it, against its evidence, its scope and the
  generality test of [Destinations](#3-destinations). A lesson no worklist holds, such as
  one a wave's last review batch adds, is read by the next review batch the campaign
  launches.
- The review batch that reads a lesson marks it `held` in its landing. A lesson it judges
  wrong, or one that belongs in the spec, is a finding of that batch: under `fix`, the
  batch corrects the entry, retires it, or files the proposal it should have been.
- A lesson the code no longer supports is `retired`. It stays in the file, marked, with
  why.
- An edit changes one entry. The file is never rewritten whole, since a rewrite drops what
  its writer did not think to keep.

The lessons are reconciled at each ship point, and whenever five have been added or changed
since the last pass: duplicates are merged, stale lessons are retired, scopes are checked,
and a lesson that can be stated without the target's names is proposed for the spec, as is
one a second campaign records again, by a proposal citing both. A lesson the pass changes
is `provisional` again.

## 6. Changes

A campaign evolves each component, Crustify or a tool, on a working branch of its own in
that component's repository, `<campaign-id>/devel`, the campaign id being the name of the
campaign's repository. It is forked from the component's `devel` when the campaign first
needs it, and the campaign's runs read and run the component from its checkout, so that a
campaign runs on what it has changed and no other campaign does.

A change is made on a branch named `<campaign-id>/evolution/<slug>`, forked from that
working branch, in a worktree beside the repository that lives only while the change is
made. A branch holds one concern. Once the change lands on the working branch, by a
fast-forward, the worktree is purged and the branch deleted. Its commits take the identity
[`versioning`](../../operations/versioning/SKILL.md)'s Identity section gives the
campaign's.

- A change to the spec follows `authoring`: written once, in the place its kind belongs,
  as generally as the evidence allows.
- A change to what a tool does comes with a regression test: the reproducer of a defect
  becomes one, and a new behaviour gets one that fails without it. A change to its
  documentation alone adds none, unless the defect it fixes has a reproducer, which becomes
  a test or a doctest. A packaging defect's reproducer becomes a test too, run
  against a build installed as a dependent installs it. The tool's whole suite passes, its
  opt-in tests included wherever the change touches what they cover.
- A new tool is drafted and tested where it serves a repeated procedure, preferably as a
  subcommand of an existing tool within that tool's goals, or as a script in the skill
  that describes its use, as `authoring` places one; a tool of its own repository is
  merged upstream only with the user's approval.

A fix that unblocks the campaign, or that would prevent a defect in later campaigns, is
landed on the working branch as soon as it is reviewed, rather than batched.

## 7. Validation

A tool's change is validated by its tests, the regression test it adds among them.

A spec change that a failure prompted is validated by running again what failed, the item,
the batch or the stage, under the change: a lightweight run, without the tests or gates
the failure does not need to show. The proposal records what the run produced before and
after, and a change whose rerun still fails does not land. A spec change no failure
prompted, such as a rule loosened or a waste removed, is validated the same way where its
effect is in doubt, on the item its evidence came from.

A rerun shows that a change answers the case that exposed it, not that it holds: that is
watched in the campaigns after it lands, as [`evolution-record`](record/SKILL.md) describes.

## 8. Review

Every change is reviewed before it lands, on its evolution branch, by a run other than the
one that made it. A change is finished once its proposal names its commit. A finished
change is reviewed before the next wave of its campaign launches, so that later runs work on
the fix rather than around it. The review reads the proposal, the change and its validation, and checks
that:

- the proposal's evidence shows the signal, and the change answers it;
- the change serves a goal, and a tool's stays within the tool's own goals;
- it is placed and written as [`authoring`](../authoring/SKILL.md) describes, and states
  no rule in the target's names;
- its validation was run, and shows what the proposal says;
- the row its proposal drafts for the record, as [`evolution-record`](record/SKILL.md) describes, names a recurrence
  signal a campaign would observe, and `test` only where its test checks all of it; and
- whether it weakens a check, which the verdict marks.

A review runs under the campaign's working branch of the component, never under the change
it reviews, and reads the change from its branch. Its task pins the commit it reviews, and
only that commit lands, by a fast-forward of the working branch: a commit added after the
verdict, or one a rebase or cherry-pick makes, is reviewed again. Its checks are this section's and its
role's; the task message of the run that asks for it adds to them, and never relaxes them.
A review reads as deeply as the change reaches: a change to documentation alone is read; a
tool's code, a check, a soundness fix and every rule of the spec are reviewed with their
validation run again.

The verdict is recorded in the proposal's Review section, approved or rejected, with its
reasons; a rejection leaves the proposal open for another change or for the user.

What only records what was decided changes no rule and is not reviewed: a row of the index,
a status of the record, or a proposal's status, verdict and review. A row of the record is
reviewed in its proposal, with its change.

A change that weakens a check, a gate, a test, a lint, a review objective, a tool's
detection or a rule of this skill, is marked so in the verdict and in its entry of the
record, since a run that can loosen what judges it passes by loosening it: the user reads
each such change on its own before `devel` takes it, as [Autonomy](#9-autonomy) describes.

## 9. Autonomy

The settings' `evolution` answer sets how far a campaign evolves the harness:

| answer | what lands on the campaign's working branches |
|---|---|
| `off` | nothing: no proposal, no lesson |
| `propose` | nothing but the index's rows and the record's statuses: proposals and lessons are filed, and no rule changes |
| `repair` | each fix of a defect |
| `evolve` | also each improvement and discovery |

A change lands on its component's working branch as soon as its review approves it, without
the user's approval: the working branch is the campaign's own, and nothing else runs on it.

The protected paths are the exception. They hold what judges the work, and a run that can
loosen what judges it passes by loosening it. In Crustify's repository they are:

- `GOALS.md`;
- `skills/crustify/evolution/**` and `skills/verification/**`, the scripts beside those
  skills included;
- `skills/artifacts/task-schema/SKILL.md`;
- the Lints section of `skills/rust/toolchain/SKILL.md`;
- the Testing, Reviewing and Audit sections of `skills/tools/*/SKILL.md`;
- `agents/common.md`, `agents/reviewer.md` and the Evolution section of
  `agents/assistant/assistant.md`; and
- `providers/generic/compose.py` and, under `providers/claude/`, `compose.py`, `spawn.py`,
  `system-prompt.md`, `hooks.json` and `agents/reviewer.md`.

In a tool's repository, they are the code whose output a gate or a review reads.
<!-- TODO: the tool skills do not list that code yet. -->

A change whose diff touches a protected path lands on the working branch only with the
user's approval, whatever its review says, and so does the removal of a `weakens a check`
mark from the record. One case lands without that approval: the repair of a defect that
blocks the campaign, once its review approves it and finds three things. The repair weakens
no check. Every existing test of the check it touches is unchanged. The repair adds a
regression test of its own. Such a repair is put to the user at the next module's end. A
change to `GOALS.md` is proposed and never made, unless the user asks for it, since
`GOALS.md` is what every other change is judged against.

A component's `devel` is the user's gate. It takes a campaign's working branch only with
the user's approval, asked for at each module's end and at the campaign's end, with the
record's entries since the last advance, those the review marked as weakening a check
first. Where `devel` has moved meanwhile, the working branch takes it by merge before it
is offered. What the user declines is reverted on the working branch or stays there, as
they say, and is recorded so; where it weakened a check, what landed under it is reviewed
again, by review batches with `revisit`, as [Adoption](#10-adoption) schedules them for a
soundness fix. Merging a component's `devel` into its `main`, and merging a
new tool upstream, need the user's approval too.

A run that a defect blocks does not work around it. Where the answer lets fixes land, it
makes the fix on its evolution branch; under `propose` it files the proposal, with its
reproducer, and the user is asked at once whether the fix is to be made; and it ends,
reporting which. The fix is reviewed and lands, and the run is run again, as a failed
batch is.

## 10. Adoption

Every run's `task.json` records the revisions of Crustify and the tools it launched
under, as [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Run fields section
describes. A change that lands on a working branch takes effect as it lands: the runs launched
after it record its revision, and a run under way when it lands, which its recorded
revisions and its landing's date tell, may have followed either. What landed before it
under the old rules stays, unless the change fixes a soundness
defect: then the landings it affects are reviewed again, by a review batch with
`revisit`.

At each module's end, the campaign's evolution is consolidated: open proposals are landed
as the autonomy allows, the working branches are offered to the user for `devel`, and the
revisit batches a soundness fix or a declined weakening calls for are scheduled. The
lessons are reconciled when [Lessons](#5-lessons) times it, and the record's rows are read
when [`evolution-record`](record/SKILL.md) times it.

## 11. The record

The record of what landed, `EVOLUTION.md`, and how evolution itself evolves from it are
[`evolution-record`](record/SKILL.md)'s.
