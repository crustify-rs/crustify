# Campaign layout

A repository holds one campaign, and its work is cumulative: a later run resumes it and
skips what it already completed. Its branches and worktrees are named from a batch's
coordinates in `crustify/artifacts/schedule.json`, its wave index and batch index, and its
artifact dirs from the agent that ran and its run number. Nothing records a path; each
name below is spelled from those coordinates.

## 1. Repository

A translation campaign produces a Rust codebase, so its repository is one: a new
repository created for the campaign, with the Rust at its root and the C it translates
inside it.

| campaign | repository | the C, under `c/` |
|---|---|---|
| wrap | `<repo>-bindings` | a submodule of the source, pinned at the campaign's revision, which the campaign never changes |
| port | `<repo>-rs` | a submodule of the campaign's fork of the source, `<repo>-fork`, on its `crustify/devel` branch, which integrations change as their modules leave C |

`<repo>` is the source repository's name: a port of libgit2 is `libgit2-rs`, with its fork
`libgit2-fork`. Both keep the C's history where it belongs, so that it can be read in the
submodule and an upstream release taken in by rebasing the fork's branch onto it. The
repositories are created under the `crustify-rs` organization, and the campaign's tree is:

```text
<repository>/
├── Cargo.toml          the safe crate, and the workspace
├── src/                the safe crate's modules, as the conventions lay them out
├── tests/              the safe crate's integration test suites
├── <link-unit>-sys/    one raw bindings crate per link unit
├── wrappers/          one wrapper crate per out-of-tree library, as dependencies.md describes
├── c/                  the C codebase, the C root
└── crustify/           the campaign: its settings, artifacts and analysis state
```

Every path into the C that the plan records, in `modules.json`, `schedule.json`, the
wavefront configurations and tables and a batch item's `defined_in`, is relative to the C
root, `c/`, so that the plan reads as the C codebase lays itself out. Every other path is
relative to the repository's root.

An audit reviews an existing Rust crate in its own repository, and creates none.

## 2. Branches

| branch | name | checked out |
|---|---|---|
| shipping | `crustify/main` | never while the campaign runs |
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

Each batch has its own worktree at `crustify/.worktrees/<its branch name>`. A planner run
has none: it runs in the repository's base dir, on its branch.

## 4. Batch ids

A batch's id is the part of its branch name after `crustify/batches/`:
`wave-<index>/batch-<index>`. It is permanent, since a wave's index is never reused (see
`specs/artifacts/schedule.md`), and its entry in `schedule.json` gives the batch's link
unit, module, kind and worklist. A run's id is `<role>/run-<n>`, which names its
artifact dir; a planner run's branch is named from it.

## 5. Artifact dirs

The campaign's artifacts sit under `crustify/artifacts/`, with one dir per agent run:

```text
crustify/artifacts/                             the campaign
├── build.json                                  the prebuilt variants of the target
├── modules.json                                the module decomposition
├── schedule.json                               the waves and batches, and their progress
├── dashboard.md                                the campaign dashboard; audit-dashboard.md for an audit
├── assistant/                                  Crustify's own records, as the assistant
│   ├── assistant-<timestamp>.session.json      one per assistant run, copied from its home
│   └── assistant-<timestamp>.usage.json        derived by `crustify usage`
├── planner/run-<n>/                            a planner run
├── binder/run-<n>/                             a binder's run of a `wrap` batch
├── translator/run-<n>/                         a translator's run of a `port` batch
├── reviewer/run-<n>/                           a reviewer's run of a review batch
│   ├── task.json                               its input, with the batch and run fields
│   ├── <role>.session.json                     written by the spawn command
│   ├── <role>.usage.json                       derived by `crustify usage`
│   └── ffimap.json                             its ffimap scan, once recorded
└── waves/wave-<index>/                         a wave's own records, such as its ffimap scan
```

Each agent's runs are numbered from 1 in the order they launch, so a batch that is run
again gets a new run dir, and every attempt keeps its records. A run's `task.json` names
its batch, and a batch's runs are those whose `task.json` names it. The run dir is what the
spawn command's `--log-dir` names, so it holds everything about the run: its input, the
model and billing it ran under, and the artifacts its agent produced.

The settings each module or wave ran under are not copied anywhere: they are
`crustify/CRUSTIFY.md` as committed at its base, in the working branch's history.

## 6. Lifecycle

Each branch, worktree and artifact dir exists only while its part of the campaign needs
it. Before a part starts, everything it is named for exists; once it is promoted, what
only it needed is purged.

### 6.1 Campaign

The working branch is created during setup, in the repository the campaign creates, with
the C under `c/` and `crustify/CRUSTIFY.md` in its first commit, together with the
campaign's artifact dir. The shipping branch is created at the same commit and stays there
until the user first approves shipping. Both last for the campaign.

The working branch is committed to only between waves, so that every promotion is a
fast-forward. The progress recorded while a wave runs, in `schedule.json` and the
dashboard, stays in the base checkout's working tree until the wave has been promoted,
and is then committed with its accounting. No agent writes `schedule.json`, so the
fast-forward never conflicts with it.

### 6.2 Planner runs

A planner run's artifact dir is created, and its branch forked from the working branch's
tip and checked out in the repository's base dir. Once the run has committed, the working
branch is checked out and fast-forwarded to it, and the next run forks from there.

### 6.3 Modules

A module has no branch of its own. Its base is the working branch's commit its first
wave forks from, which holds its scaffolded `.rs` file and the settings it runs under. Its
end state is the working branch's commit its last wave is promoted to.

### 6.4 Waves

A wave's integration branch is forked from the working branch's tip before any of its
batches launch; that commit is the wave's base. The branch exists before the first
landing, because a landing push to a missing branch silently creates it, and is never
checked out. Once every batch has landed, the working branch is fast-forwarded to the
wave's tip.

A review wave forks once the wave it reviews has been promoted, so the reviewed commits
are on the working branch, and their batches' `commits` in `schedule.json`.

### 6.5 Batches

A batch's run dir, with its `task.json`, and its branch and worktree, forked from its wave
branch's tip, are created before it launches. The gitignored state its tree needs and does
not build itself, such as shared analysis databases, is symlinked from the base checkout,
and its `c/` is a worktree of the base checkout's submodule at the commit the superproject
records, since no batch changes the C.
Once the batch has landed, its worktree is purged; its branch stays until its commits are
recorded in `schedule.json`, since they are derived from it, as
[`landing.md`](landing.md) describes. A batch that fails keeps its branch and worktree for
inspection; they are removed before it is run again, which forks them anew.

## 7. Crustify's home

Crustify keeps what belongs to its user rather than to a campaign in its home,
`$CRUSTIFY_HOME` or `~/.crustify`:

```text
~/.crustify/
├── providers/codex/                  Codex's home under API-key billing
├── sessions/<session id>/            one assistant session
│   ├── index.json                    where it runs and its repository, for `--resume`
│   ├── workdir                       the repository it established, when it opened outside it
│   └── assistant-<timestamp>.*       its session and usage records, one per run
└── transcripts/<session id>.jsonl    the agents' transcripts, copied from the CLIs' homes
```

An assistant session's records live in its directory there from its first turn, so a
session can open before its repository is established: it opens on the repository when the
directory it starts in holds `crustify/CRUSTIFY.md`, and that file is written once the
repository is established otherwise. The records are copied into the repository's
`crustify/artifacts/assistant/`, where the campaign tracks them. A session's directory is
named by crustify's id for it, which is its CLI's own session id under Claude Code.

## 8. Scratch

`crustify/tmp/` is gitignored and holds anything residual that is no artifact: downloads,
scratch builds and experiments, intermediate outputs. Residual files go nowhere else in the
repository.

## 9. Reviews

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`,
`crustify/reviews/wave-<index>/batch-<index>/`, in the repository the review lands in: one `<slug>` directory per finding, holding its report
and, when it has one, its reproducer, under the sub-directory of the finding's kind.

A planner that amends an earlier plan files its findings the same way under
`crustify/reviews/planner/`: `modules/` for `modules.json` and `schedule.json`, and
one sub-directory per skill artifact it amends.
