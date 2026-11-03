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

A library the target uses from outside its tree is wrapped in a wrap campaign of its own,
in `<source>-bindings`, named after the source it is built from, as
[`dependencies.md`](dependencies.md) describes.

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
   [`testing.md`](testing.md)'s Regressions section describes, fixing what fails;
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
