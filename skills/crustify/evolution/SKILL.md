---
name: evolution
description: "How Crustify repairs and improves itself from what its campaigns expose: goals, signals, proposals, lessons, evolution branches, validation, review, autonomy, adoption, the record of what landed and how evolution itself evolves. Read before filing a defect in Crustify or a tool, proposing or making a change to either, or recording a campaign's lesson."
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

A proposal is filed in the campaign's repository under `crustify/evolution/<slug>/`, as
its `PROPOSAL.md`: the signal and its evidence, with the runs, findings and commits it
cites; its destination; the change, or the patch; how it was validated; its review's
verdict; and its status, `open`, `landed`, with the commit it landed as, or `declined`,
with why. A lesson is not
filed as a proposal: `LESSONS.md` records it.

A defect in a tool found while reviewing is such a proposal, not a finding on the reviewed
code, and is filed with its reproducer.

## 5. Lessons

The campaign's lessons sit in `crustify/LESSONS.md`, read by every run of the campaign
before its first step. Each is one rule, with the evidence it rests on and its scope, the
modules, items or stages it holds for. A lesson a second campaign records again is
generalized into the spec, by a proposal citing both.

## 6. Changes

A change is made on a branch of the component's repository named
`<campaign-id>/evolution/<slug>`, the campaign id being the name of the campaign's
repository, from the component's `devel`, in a worktree beside that repository that lives
only while the change is made. A branch holds one concern. Once the change lands on
`devel`, the worktree is purged and the branch deleted. Its commits take the identity
[`versioning`](../../operations/versioning/SKILL.md)'s Identity section gives the
campaign's.

- A change to the spec follows `authoring`: written once, in the place its kind belongs,
  as generally as the evidence allows.
- A change to a tool comes with a regression test, whatever it changes: the reproducer of
  a defect becomes one, a new behaviour gets one that fails without it, and the tool's
  whole suite passes.
- A new tool is drafted and tested where it serves a repeated procedure, preferably as a
  subcommand of an existing tool within that tool's goals, or as a script in the skill
  that describes its use, as `authoring` places one; a tool of its own repository is
  merged upstream only with the user's approval.

A fix that unblocks the campaign, or that would prevent a defect in later campaigns, is
landed on `devel` as soon as the autonomy allows, rather than batched.

## 7. Validation

A tool's change is validated by its tests, the regression test it adds among them.

A spec change that a failure prompted is validated by running again what failed, the item,
the batch or the stage, under the change: a lightweight run, without the tests or gates
the failure does not need to show. The proposal records what the run produced before and
after, and a change whose rerun still fails does not land. A spec change no failure
prompted, such as a rule loosened or a waste removed, is validated the same way where its
effect is in doubt, on the item its evidence came from.

A rerun shows that a change answers the case that exposed it, not that it holds: that is
watched in the campaigns after it lands, as [Record](#11-record) describes.

## 8. Review

Every change is reviewed before it lands, on its evolution branch, by a run other than the
one that made it. The review reads the proposal, the change and its validation, and checks
that:

- the proposal's evidence shows the signal, and the change answers it;
- the change serves a goal, and a tool's stays within the tool's own goals;
- it is placed and written as [`authoring`](../authoring/SKILL.md) describes, and states
  no rule in the target's names;
- its validation was run, and shows what the proposal says; and
- it weakens no check.

The verdict is recorded in the proposal: approved, or rejected, with why, which leaves the
proposal open for another change or for the user.

A change that weakens a check, a gate, a test, a lint, a review objective, a tool's
detection or a rule of this skill, is not approved by the review alone, whatever the
autonomy: it is put to the user with the review's reading, since a run that could loosen
what judges it would pass by loosening it.

## 9. Autonomy

The settings' `evolution` answer sets how far a campaign evolves the harness:

| answer | what lands |
|---|---|
| `off` | nothing: no proposal, no lesson |
| `propose` | proposals and lessons; nothing of Crustify or a tool changes |
| `repair` | also each fix of a defect, on its component's `devel`, once approved |
| `evolve` | also each improvement and discovery, on `devel`, once approved |

Its `unattended` part says how long a change lands on `devel` without the user's approval:
until the next ship point, across a number of modules, or for the whole campaign: the
review's approval then stands in for the user's. Without
it, the user approves each change: a fix that unblocks a run as soon as it is made, and
every other at the next module's end, or at an audit's end. Merging a component's `devel`
into its `main`, merging a new tool upstream, and changing `GOALS.md` or this skill always
need the user's approval.

A run that a defect blocks does not work around it. Where the answer lets fixes land, it
makes the fix on its evolution branch; under `propose` it files the proposal, with its
reproducer; and it ends, reporting which. The fix is reviewed, and lands at once where
`unattended` covers it. Otherwise the user is asked at once: to approve the fix, or, under `propose`, whether it
is to be made. The run is run again once the fix has landed, as a failed batch is.

## 10. Adoption

Every run's `task.json` records the revisions of Crustify and the tools it launched
under, as [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Run fields section
describes. A change that lands on `devel` takes effect as it lands: the runs launched
after it record its revision, and a run under way when it lands, which its recorded
revisions and its landing's date tell, may have followed either. What landed before it
under the old rules stays, unless the change fixes a soundness
defect: then the landings it affects are reviewed again, by a review batch with
`revisit`.

At each module's end, the campaign's evolution is consolidated: recurring lessons are
proposed for the spec, open proposals are landed as the autonomy allows or put to the
user, the revisit batches a soundness fix calls for are scheduled, and the watched changes
of the record are checked against the module.

## 11. Record

Every change that lands is recorded in Crustify's own repository, in
[`EVOLUTION.md`](../../../EVOLUTION.md), whatever component it changed, so that a later
campaign can tell whether it held. An entry gives the campaign and proposal the change
came from, the component and commit it landed as, the signal it answered, its recurrence
signal and its status.

The recurrence signal is what a campaign would observe if the issue were back, in what a
campaign produces anyway: a review finding of a category, a run that fails for a cause, a
tool's error, a correction the user repeats. A change whose regression test checks all of
it has `test` in its place and is not watched. One with no signal a campaign could observe
has `none`, with why, and is not watched either.

A watched change is checked at each module's end, in every campaign, against that module's
findings, failed runs, proposals and corrections. It is:

- `watched` from its landing;
- `recurred` once its signal is met again, with the evidence, which opens a proposal that
  cites the entry: the change was wrong or partial, or the validation and review that
  passed it were; and
- `confirmed` once a campaign other than the one it came from has ended, having exercised
  it, without the signal.

The record is committed on `devel` at each module's end, in a commit of its own.

## 12. Evolving evolution

Evolution evolves from its own record, as everything else does from a campaign's. At a
campaign's end the record and the campaign's proposals are read for what repeats: changes
that recurred; changes the review rejected or the user declined, by cause; signals a run
met that no proposal answered; and how long a blocking defect held its run. Each is a
signal of this guidance, as [Signals](#2-signals) lists them, and its proposal is on this
skill, on the agents' evolution rules or on what the review checks.

Such a proposal is validated and reviewed as any other, and lands only with the user's
approval, as [Autonomy](#9-autonomy) describes, so that the mechanism never loosens what
checks it.
