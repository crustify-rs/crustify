---
name: versioning
description: "Repositories, branches, worktrees, landing under the landing lock, promotion, integration, their lifecycle, and the identity every commit takes. Read before the first commit, and before creating, landing on, promoting or purging any branch or worktree."
---

# Versioning

How a campaign's work is held in version control: the repositories it works in, their
branches and worktrees, how a batch lands its work and how each part is promoted. Where
things sit in the tree is [`layout`](../layout/SKILL.md)'s.

## 1. Repositories

A translation campaign produces a Rust codebase, so its repository is one: a new
repository created for the campaign, with the Rust at its root and the C it translates
inside it.

| campaign | repository | the C, under `c/` |
|---|---|---|
| wrap | `<repo>-crustify` | a submodule of the source, pinned at the campaign's revision, which the campaign never changes |
| port | `<repo>-crustify` | a submodule of the campaign's fork of the source, `<repo>-fork`, on its `main` branch, which integrations trim as their modules leave C |

`<repo>` is the source repository's name: a campaign on libgit2 is `libgit2-crustify`,
and a port's fork `libgit2-fork`. A wrap and a port campaign share the name, since wrapping a
codebase is a step towards replacing its implementation: a port continues a wrap campaign
in its repository. Both keep the C's history where it belongs, so that it can be read in the
submodule and an upstream release taken in by rebasing the fork's `main` onto it. The fork
mirrors the source's own `main` as `upstream/main`. The repositories are created under the
`crustify-rs` organization; the campaign's tree is [`layout`](../layout/SKILL.md)'s.

A library the target uses from outside its tree is wrapped in a wrap campaign of its own,
in `<source>-crustify`, named after the source it is built from, as
[`dependencies`](../../planning/dependencies/SKILL.md) describes.

An audit reviews an existing Rust crate in its own repository, and creates none.

## 2. Branches

| branch | name | checked out |
|---|---|---|
| shipping | `main` in the campaign's own repository; `crustify/main` in an audit, beside the reviewed crate's own branches | never while the campaign runs |
| working | `crustify/devel` | in the repository's base dir |
| planner run | `crustify/planner/run-<n>` | in the repository's base dir, while its run is live |
| module | `crustify/modules/<link-unit>/<module>`, or `crustify/foundational/<link-unit>/<module>` for a foundational module | in its worktree, while it integrates |
| wave | `crustify/waves/wave-<index>` | never |
| batch | `crustify/batches/wave-<index>/batch-<index>` | in its worktree |

The shipping branch holds what the user has approved to ship: it advances only with the
user's approval, by a fast-forward to the working branch, and each advance is tagged on it,
`ship-<n>` numbered from 1, or `crustify/ship-<n>` in an audit. The working branch is where the
campaign integrates its work: planner runs fork from it and are promoted back to it, and
the modules are integrated into it, as `scheduling` describes.

A module's branch holds one run of its waves: its waves fork from
it and are promoted back to it, and it is integrated into the working branch once they
have landed, as [Integration](#45-integration) describes. `<module>` is the module's
`name`, the path of its TU or header below the C root; a path is never a directory of
another, so no two module branches collide.

A wave's branch is the integration branch its batches land on, a review wave's as much as
a translation wave's. It is never checked out: a landing push to a checked-out branch
fails, and one to a missing branch silently creates it.

An audit has no link units or modules: its waves are review waves, laid out the same
way.

## 3. Worktrees

Each batch has its own worktree, its `c/` a worktree of the base checkout's submodule, at
`crustify/.worktrees/<module dir>/<batch id>`, named as
[`layout`](../layout/SKILL.md)'s Ids section names them, so that its name tells which
module it works on, and so does a module while it integrates, at
`crustify/.worktrees/<module dir>/integration`, beside its batches'. A
planner run has none: it runs in the repository's base dir, on its branch.

## 4. Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work. A commit carries
no trailer but the co-author trailers of the campaign's [identity](#6-identity), and its
subject says what it does and which run made it. A batch's names its module's file and its
objective and ends with its run's id, as `refs.c: wrap 12 items (wave-3/batch-1/run-2)`,
and its body lists the items it translated by their anchors' paths, as
`fn::git_reference_lookup`, one per line; a review batch's two commits name what they file
and what they fix the same way, and a planner run's subject ends with its run's id. A
progress commit is `progress: wave-<index>`, and an integration's merge, in the campaign's
repository and on the fork's `main`, `integrate <module>`, the module written as
[`modules-schema`](../../artifacts/modules-schema/SKILL.md) writes it.

The landing operation is a local push of the batch's tip to the integration branch through
the repository's Git common directory, which accepts only a fast-forward. A direct ref
update is no substitute: its compare-and-swap form makes the update atomic, but does not
enforce that the new commit descends from the expected old commit.

### 4.1 The landing lock

An integration branch is landed on by one batch at a time, under its landing lock: an
exclusive `flock` on a file in the Git common directory, named after the branch with its
`refs/heads/` prefix dropped, so that every worktree of the repository sees the same lock:

```text
$(git rev-parse --git-common-dir)/crustify/landing/<integration branch>.lock
```

A batch whose validated work is committed on its own branch takes the lock and holds it
until its landing has succeeded:

1. it acquires the lock, waiting while another batch holds it;
2. it rebases only its own branch onto the current integration branch, once: nothing else
   lands while it holds the lock;
3. it resolves any conflict the rebase raises and runs again, on the rebased tree, the
   gates that could catch a regression of the integration, as
   [`testing-gates`](../../verification/testing/gates/SKILL.md)'s Regressions section describes, fixing what fails;
4. it pushes the fast-forward, which nothing can reject; and
5. it releases the lock.

A conflict or a failing gate is resolved under the lock rather than after releasing it, so
that the branch cannot move again in between and no batch rebases twice.

The waiter blocks in `flock` itself, so the kernel wakes it the moment the lock is released,
and nothing polls. Once it holds the lock, it hands the locked descriptor to a process of
its own, detached from the shell that started it and bound to the lifetime of the agent's
CLI: a `flock` lock belongs to the open file, so that process keeps it after the command
that took it exits, until the agent ends, however it ends, and the kernel releases it. The
holder records itself beside the lock, in `<integration branch>.lock.holder`, as its own pid
and the CLI's. A waiter bounds each wait, to stay within the time a single command may run,
and waits again when it expires. For example, with `$CLI_PID` the agent CLI's pid, found by
walking up the shell's parent processes:
<!-- TODO: this procedure must run exactly so: it belongs in a script beside this skill,
documented by its `--help`, as `authoring` describes. -->

```bash
lock="$(git rev-parse --git-common-dir)/crustify/landing/<integration branch>.lock"
mkdir -p "$(dirname "$lock")"
# wait in the kernel, up to 10 minutes per command; then hand the lock to a detached holder
sh -c '
  exec 9>"$1"
  flock -w 600 9 || exit 1
  setsid sh -c "echo \"\$\$ $2\" > \"$1.holder\"; exec tail --pid=$2 -f /dev/null" 9>&9 &
' sh "$lock" "$CLI_PID"
# release, once the push has succeeded
holder=$(cut -d' ' -f1 "$lock.holder"); rm -f "$lock.holder"; kill "$holder"
```

The holder file is removed before the holder is ended, while the lock is still held, so
that a release never removes the next holder's record.

The lock has no timeout: the regression gates it covers vary in length. A holder that has
stopped making progress keeps it until its agent is ended, which releases it; the batch is
then run again, as any failed batch is.

### 4.2 Commits

Every landing is a fast-forward, so an integration branch is linear, and each batch's
commits are one unbroken run of it, ending at its branch's tip and starting after the wave
base or the tip of the batch that landed before it: the commits its branch reaches and
neither the wave base nor the wave's other landed batches reach, oldest first, which
become the batch's `commits` in `schedule.json`.

The integration branch is never reset, force-updated or moved backward, and nothing is
pushed to a remote. The worktree stays after landing, until it is purged as [Lifecycle](#5-lifecycle)
describes.

### 4.3 Promotion

A wave that has landed every batch is promoted to the branch it forked from, the module's
branch or the working branch, by a fast-forward to its tip, with the same local push
through the Git common directory, which rejects anything but a fast-forward.

### 4.4 Progress

The progress recorded while waves run, in `schedule.json` and the dashboard's usage and
campaign cells, is committed on the working branch whenever no module is integrating. No agent writes
`schedule.json`, and no module branch changes it.

### 4.5 Integration

A module's branch is integrated into the working branch once the
last wave of its run has been promoted to it. Other modules may have been integrated since
it forked, so the working branch is merged into it, in its worktree, rather than the
other way around: the module's commits keep their ids, which its batches' `commits`
record, and the working branch still moves only by fast-forward.

1. The working branch's tip is merged into the module's branch. The files every module
   adds to, the dashboard's rows, the raw bindings' allowlists, `src/lib.rs`'s module
   declarations and the safe crate's export features, conflict additively: each conflict
   keeps both sides, and the generated bindings are regenerated from the merged input. Any other conflict is a defect of the integration, resolved without
   discarding either side.
2. The merge's tree passes the gates of
   [`testing-gates`](../../verification/testing/gates/SKILL.md)'s Regressions section, and in
   a port campaign, in the run that holds the last wave of the module's `wrap` and `port`
   items, the module's integration from C, which happens once, as
   [`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Builds section describes:
   its export feature is deleted, and the C test cases none of its `unit_pub` tests carries
   over are listed before its C tests leave.
3. The working branch is fast-forwarded to the module's branch.

Modules integrate one at a time, and nothing else is committed on the working branch while
one does, so that its fast-forward cannot be rejected. A port's later-stage waves come after
their module's integration, are promoted to the working branch, and integrate nothing, as
the porting workflow's Later stages section describes.

## 5. Lifecycle

Each branch and worktree exists only while its part of the campaign needs it. Before a part starts, everything it is named for exists; once it is promoted, what
only it needed is purged.

### 5.1 Campaign

The working branch is created during setup, in the repository the campaign creates, with
the C under `c/` and `crustify/CRUSTIFY.md` in its first commit. The shipping branch is created at the same commit and stays there
until the user first approves shipping. Both last for the campaign.

The working branch is committed to only when nothing is being promoted or integrated to
it, so that every promotion and integration is a fast-forward: the progress recorded in
the meantime stays in the base checkout's working tree until then, as
[Progress](#44-progress) describes.

### 5.2 Planner runs

A planner run's branch is forked from the working branch's tip and checked out in the repository's base dir. Once the run has committed, the working
branch is checked out and fast-forwarded to it, and the next run forks from there.

### 5.3 Modules

A module's base is the working branch's commit that holds its scaffolded `.rs` file and
the settings it runs under, committed before its first wave.

A module's branch is forked from its base before its first wave,
once the waves of other modules that its waves depend on have been integrated. A module
whose waves the order splits, such as one that wraps a cut dependency ahead of its
consumer, runs once per contiguous run of its waves, each run on a branch forked anew
from the working branch. In a port campaign, only the run that holds the last wave of the
module's `wrap` and `port` items integrates it from C; an earlier run's integration merges
its Rust alone, the module still C. Once a run has been integrated, its branch and worktree
are purged; its end state is the working branch's commit its last run integrates into.

### 5.4 Waves

A wave's integration branch is forked from its module's branch's tip, or, for a port's
later-stage wave, which runs after its module's integration, from the working branch's tip,
before any of its batches launch, so that it exists before the first landing, as [Branches](#2-branches)
requires; that commit is the wave's base.
Once every batch has landed, the wave is promoted, as [Promotion](#43-promotion)
describes, and its branch purged.

A translation wave's review batches are batches of the wave itself, and it is promoted once
they have landed too. An audit's review waves fork as any wave does.

### 5.5 Batches

A batch's branch and worktree, forked from its wave branch's tip, are created before it
launches, with its run dir, as [`layout`](../layout/SKILL.md) describes. The gitignored state its tree needs and does
not build itself, such as shared analysis databases, is symlinked from the base checkout,
and its `c/` is a worktree of the base checkout's submodule at the commit the superproject
records, since no batch changes the C.
Once the batch has landed, its worktree is purged; its branch stays until its commits are
recorded in `schedule.json`, since they are derived from it, as
[Landing](#4-landing) describes. A batch that fails keeps its branch and worktree for
inspection; they are removed before it is run again, which forks them anew.

## 6. Identity

Every commit of a campaign, in its repository and its wrappers', is authored and committed
as Crustify, whose GitHub account is `crustify-ai` and whose git identity is
`crustify <crustify@berkeley.edu>`, whatever the repository's git configuration says,
unless the settings' `identity` answer names another: an author and any co-authors, each
as `Name <email>`. The author named there then authors and commits every commit, and each
message ends with one `Co-Authored-By:` trailer per co-author and no other, none that an
agent's host suggests included.

The identity is passed explicitly, as configuration on the command line, to every command
that writes a commit, a rebase, a merge and a cherry-pick as much as a commit, since the
host may have no git identity of its own.
