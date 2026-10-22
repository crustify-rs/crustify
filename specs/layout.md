# Campaign layout

Where a campaign's files sit: the repository's tree, its artifact dirs, Crustify's home
and the campaign's scratch and reviews dirs. The repositories, branches and worktrees
that hold them are [`versioning.md`](versioning.md)'s.

A repository holds one campaign, and its work is cumulative: a later run resumes it and
skips what it already completed. Its artifact dirs are named from the agent that ran and
its run number, and a batch's from its coordinates in `crustify/artifacts/schedule.json`,
its wave index and batch index. Nothing records a path; each name below is spelled from
those coordinates.

## 1. Tree

A translation campaign's repository, as [`versioning.md`](versioning.md)'s Repositories
section names it, is laid out as:

```text
<repository>/
├── Cargo.toml          the safe crate, and the workspace
├── src/                the safe crate's modules, as the conventions lay them out
├── tests/              the safe crate's integration test suites
├── <link-unit>-sys/    one raw bindings crate per link unit
├── wrappers/           one wrapper crate per out-of-tree library, as dependencies.md describes
├── c/                  the C codebase, the C root
└── crustify/           the campaign: its settings, artifacts and analysis state
```

Every path into the C that the plan records, in `modules.json`, `schedule.json`, the
wavefront configurations and tables and a batch item's `defined_in`, is relative to the C
root, `c/`, so that the plan reads as the C codebase lays itself out. Every other path is
relative to the repository's root.

## 2. Batch ids

A batch's id is the part of its branch name after `crustify/batches/`:
`wave-<index>/batch-<index>`. It is permanent, since a wave's index is never reused (see
`specs/artifacts/schedule.md`), and its entry in `schedule.json` gives the batch's link
unit, module, kind and worklist. A run's id is `<role>/run-<n>`, which names its
artifact dir; a planner run's branch is named from it.

## 3. Artifact dirs

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

## 4. Lifecycle

A run's dir, with its `task.json`, is created before its agent launches, and kept: every
attempt keeps its records. The campaign's artifact dir is created during setup, with the
working branch.

## 5. Crustify's home

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

## 6. Scratch

`crustify/tmp/` is gitignored and holds anything residual that is no artifact: downloads,
scratch builds and experiments, intermediate outputs. Residual files go nowhere else in the
repository.

## 7. Reviews

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`,
such as `crustify/reviews/wave-3/batch-1/`, in the repository the review lands in: one `<slug>` directory per finding, holding its report
and, when it has one, its reproducer, under the sub-directory of the finding's kind.

A planner that amends an earlier plan files its findings the same way under
`crustify/reviews/planner/`: `modules/` for `modules.json` and `schedule.json`, and
one sub-directory per skill artifact it amends.
