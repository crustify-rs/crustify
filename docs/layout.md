# Campaign layout

A repository holds one campaign, and its work is cumulative: a later run resumes it and
skips what it already completed. Its branches, worktrees and artifact dirs are all derived
from the same coordinates: the link unit, the subsystem, the wave index and the batch
index. Nothing records a path; each name below is spelled from those coordinates.

## 1. Branches

| branch | name | checked out |
|---|---|---|
| campaign | `crustify/main` | in the repository's base dir, between subsystems |
| planner run | `crustify/planning/run-<index>` | in the repository's base dir, while its run is live |
| subsystem | `crustify/subsystems/<link-unit>/<subsystem>` | in the repository's base dir, while live |
| wave | `crustify/waves/<link-unit>/<subsystem>/wave-<index>` | never |
| batch | `crustify/batches/<link-unit>/<subsystem>/wave-<index>/batch-<index>` | in its worktree |
| review wave | `crustify/reviews/<link-unit>/<subsystem>/wave-<index>` | never |
| review batch | `crustify/review-batches/<link-unit>/<subsystem>/wave-<index>/batch-<index>` | in its worktree |

A wave or review wave branch is the integration branch its batches land on. It is never
checked out: a landing push to a checked-out branch fails, and one to a missing branch
silently creates it.

An audit has no link units, subsystems or translated waves: its review waves sit directly
under the campaign, and each is promoted to the campaign branch once it lands.

| branch | name | checked out |
|---|---|---|
| campaign | `crustify/main` | in the repository's base dir |
| review wave | `crustify/reviews/wave-<index>` | never |
| review batch | `crustify/review-batches/wave-<index>/batch-<index>` | in its worktree |

## 2. Worktrees

Each batch and review batch has its own worktree at `crustify/.worktrees/<its branch name>`.
A planner run has none: it runs in the repository's base dir, on its branch.

## 3. Batch ids

A batch's id is the part of its branch name after `crustify/batches/` or
`crustify/review-batches/`: `<link-unit>/<subsystem>/wave-<index>/batch-<index>`, or
`wave-<index>/batch-<index>` in an audit. It gives the batch's link unit,
subsystem and wave. A planner run's id is `planning/run-<index>`, the part of its branch
name after `crustify/`, which names its artifact dir likewise.

## 4. Artifact dirs

Every level of a campaign has an artifact dir under `crustify/artifacts/`:

```text
crustify/artifacts/                             the campaign
├── build.json                                  the prebuilt variants of the target
├── subsystems.json                             the subsystem decomposition, in execution order
├── dashboard.md                                the campaign dashboard; audit-dashboard.md for an audit
├── planning/run-<index>/                       a planner run: its task.json, session and usage records
├── assistant/                                  Crustify's own records, as the assistant
│   ├── assistant-<timestamp>.session.json      one per assistant run, copied from its home
│   └── assistant-<timestamp>.usage.json        derived by `crustify usage`
└── <link-unit>/<subsystem>/                    a subsystem
    ├── schedule.json                           its waves and batches
    ├── wave-<index>/                           a wave
    │   └── batch-<index>/                      a batch
    │       ├── task.json                       its schedule.json entry, with the run fields
    │       ├── <role>.session.json             binder, translator or reviewer
    │       └── <role>.usage.json               derived by `crustify usage`
    └── review-wave-<index>/                    a review wave
        └── batch-<index>/                      a review batch, laid out as a batch
```

An audit's review waves sit directly in the campaign's artifact dir, as
`crustify/artifacts/review-wave-<index>/batch-<index>/`.

Each level also holds its `ffimap.json` once its ffimap scan is recorded. A batch's artifact
dir holds its `task.json` and is what its `--log-dir` names, so it holds everything about
that batch: its input, the model and billing it ran under, and the artifacts its agent
produced.

The settings each subsystem or review wave ran under are not copied anywhere: they are
`crustify/CRUSTIFY.md` as committed when it started, in the campaign branch's history.

## 5. Lifecycle

Each branch, worktree and artifact dir exists only while its level of the campaign needs
it. Before a level starts, everything it is named for exists; once it is promoted, what
only it needed is purged.

### 5.1 Campaign

The campaign branch and the campaign's artifact dir are created during setup, the branch
from the repository's revision with `crustify/CRUSTIFY.md` as its first commit. They last
for the campaign.

### 5.2 Planner runs

A planner run's branch is forked from the campaign branch's tip and checked out in the
repository's base dir, beside the run's artifact dir. Once the run has committed, the
campaign branch is fast-forwarded to it, and the next run forks from there.

### 5.3 Subsystems

A subsystem's branch is forked from the campaign branch's tip when the subsystem starts,
and checked out in the repository's base dir: it needs no worktree of its own. The commit
it starts from, with the subsystem's Rust root scaffolded, is the subsystem's base. Once
its last wave is promoted, the subsystem is promoted to the campaign branch.

### 5.4 Waves

A wave's integration branch is forked from its subsystem branch's tip, and its artifact
dir created, before any of its batches launch. Its starting commit is the wave's base. The
branch exists before the first landing, because a landing push to a missing branch
silently creates it, and is never checked out. Once the wave, and its review wave when
review is enabled, has landed, its tip is promoted to the subsystem branch.

### 5.5 Batches

A batch's artifact dir, with its `task.json`, and its branch and worktree, forked from its
integration branch's tip, are created before it launches. The gitignored state its tree
needs and does not build itself, such as shared analysis databases, is symlinked from the
base checkout. Once the batch has landed, its worktree is purged. A batch that fails keeps
its branch and worktree for inspection until they are removed.

### 5.6 Review waves

A review wave's integration branch is forked from the tip of the wave it reviews, and its
review batches are laid out as batches. Once it has landed, the reviewed tip is promoted to
the subsystem branch and its worktrees are purged. In an audit, a review wave forks from
the campaign branch's tip and is promoted back to it.

## 6. Crustify's home

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

## 7. Scratch

`crustify/tmp/` is gitignored and holds anything residual that is no artifact: downloads,
scratch builds and experiments, intermediate outputs. Residual files go nowhere else in the
repository.

## 8. Reviews

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`, in
the repository the review lands in: one `<slug>` directory per finding, holding its report
and, when it has one, its reproducer, under the sub-directory of the finding's kind.

A planner that amends an earlier plan files its findings the same way under
`crustify/reviews/planner/`: `subsystems/` for `subsystems.json` and `schedule.json`, and
one sub-directory per skill artifact it amends.
