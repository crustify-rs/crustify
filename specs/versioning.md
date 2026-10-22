# Versioning

How a campaign's work is held in version control: the repositories it works in, their
branches and worktrees, how a batch lands its work and how each part is promoted. Where
things sit in the tree is [`layout.md`](layout.md)'s.

## 1. Repositories

A translation campaign produces a Rust codebase, so its repository is one: a new
repository created for the campaign, with the Rust at its root and the C it translates
inside it.

| campaign | repository | the C, under `c/` |
|---|---|---|
| wrap | `<repo>-bindings` | a submodule of the source, pinned at the campaign's revision, which the campaign never changes |
| port | `<repo>-rs` | a submodule of the campaign's fork of the source, `<repo>-fork`, on its `main` branch, which integrations trim as their modules leave C |

`<repo>` is the source repository's name: a port of libgit2 is `libgit2-rs`, with its fork
`libgit2-fork`. Both keep the C's history where it belongs, so that it can be read in the
submodule and an upstream release taken in by rebasing the fork's `main` onto it. The fork
mirrors the source's own `main` as `upstream/main`. The repositories are created under the
`crustify-rs` organization; the campaign's tree is [`layout.md`](layout.md)'s.

An audit reviews an existing Rust crate in its own repository, and creates none.

## 2. Branches

| branch | name | checked out |
|---|---|---|
| shipping | `main` in the campaign's own repository; `crustify/main` in an audit, beside the reviewed crate's own branches | never while the campaign runs |
| working | `crustify/devel` | in the repository's base dir |
| planner run | `crustify/planner/run-<n>` | in the repository's base dir, while its run is live |
| wave | `crustify/waves/wave-<index>` | never |
| batch | `crustify/batches/wave-<index>/batch-<index>` | in its worktree |

The shipping branch holds what the user has approved to ship: it advances only with the
user's approval, by a fast-forward to the working branch. The working branch is where the
campaign integrates its work: planner runs and waves fork from it and are promoted back to
it.

A wave's branch is the integration branch its batches land on, a review wave's as much as
a translation wave's. It is never checked out: a landing push to a checked-out branch
fails, and one to a missing branch silently creates it.

An audit has no link units or modules: its waves are review waves, laid out the same
way.

## 3. Worktrees

Each batch has its own worktree at `crustify/.worktrees/<its branch name>`, its `c/` a
worktree of the base checkout's submodule. A planner run has none: it runs in the
repository's base dir, on its branch.

## 4. Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work. A commit carries
no trailer: what ties it to its batch is the batch's branch, whose tip it is or precedes.

The landing operation is a local push through the Git common directory:

```bash
git push "$(git rev-parse --git-common-dir)" HEAD:refs/heads/<integration branch>
```

`git update-ref` is no substitute: its compare-and-swap form makes the ref update atomic,
but does not enforce that the new commit descends from the expected old commit.

On a non-fast-forward rejection, the batch:

1. rebases only its own branch onto the current integration branch;
2. reruns its validation; and
3. retries the fast-forward.

Every landing is a fast-forward, so an integration branch is linear, and each batch's
commits are one unbroken run of it, ending at its branch's tip and starting after the wave
base or the tip of the batch that landed before it:

```bash
git rev-list --reverse <batch branch> --not <wave base> <the wave's other landed batch branches>
```

They become the batch's `commits` in `schedule.json`.

The integration branch is never reset, force-updated or moved backward, and nothing is
pushed to a remote. The worktree stays after landing, until it is purged as [Lifecycle](#5-lifecycle)
describes.

## 5. Lifecycle

Each branch and worktree exists only while its part of the campaign needs it. Before a part starts, everything it is named for exists; once it is promoted, what
only it needed is purged.

### 5.1 Campaign

The working branch is created during setup, in the repository the campaign creates, with
the C under `c/` and `crustify/CRUSTIFY.md` in its first commit. The shipping branch is created at the same commit and stays there
until the user first approves shipping. Both last for the campaign.

The working branch is committed to only between waves, so that every promotion is a
fast-forward. The progress recorded while a wave runs, in `schedule.json` and the
dashboard, stays in the base checkout's working tree until the wave has been promoted,
and is then committed with its accounting. No agent writes `schedule.json`, so the
fast-forward never conflicts with it.

### 5.2 Planner runs

A planner run's branch is forked from the working branch's tip and checked out in the repository's base dir. Once the run has committed, the working
branch is checked out and fast-forwarded to it, and the next run forks from there.

### 5.3 Modules

A module has no branch of its own. Its base is the working branch's commit its first
wave forks from, which holds its scaffolded `.rs` file and the settings it runs under. Its
end state is the working branch's commit its last wave is promoted to.

### 5.4 Waves

A wave's integration branch is forked from the working branch's tip before any of its
batches launch; that commit is the wave's base. The branch exists before the first
landing, because a landing push to a missing branch silently creates it, and is never
checked out. Once every batch has landed, the working branch is fast-forwarded to the
wave's tip.

A review wave forks once the wave it reviews has been promoted, so the reviewed commits
are on the working branch, and their batches' `commits` in `schedule.json`.

### 5.5 Batches

A batch's branch and worktree, forked from its wave branch's tip, are created before it
launches, with its run dir, as [`layout.md`](layout.md) describes. The gitignored state its tree needs and does
not build itself, such as shared analysis databases, is symlinked from the base checkout,
and its `c/` is a worktree of the base checkout's submodule at the commit the superproject
records, since no batch changes the C.
Once the batch has landed, its worktree is purged; its branch stays until its commits are
recorded in `schedule.json`, since they are derived from it, as
[Landing](#4-landing) describes. A batch that fails keeps its branch and worktree for
inspection; they are removed before it is run again, which forks them anew.
