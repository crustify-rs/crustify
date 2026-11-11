---
name: layout
description: "Where a campaign's files sit: the tree, batch ids, artifact dirs, Crustify's home, scratch and reviews dirs. Read before creating run dirs or placing any campaign file."
---

# Campaign layout

Where a campaign's files sit: the repository's tree, its artifact dirs, Crustify's home
and the campaign's scratch and reviews dirs. The repositories, branches and worktrees
that hold them are [`versioning`](../versioning/SKILL.md)'s.

A repository holds one campaign, and its work is cumulative: a later run resumes it and
skips what it already completed. Its artifact and reviews dirs are grouped by module, and
named from a batch's coordinates in `crustify/artifacts/schedule.json`, its module, wave
index and batch index, and a run's attempt. Nothing records a path; each name below is
spelled from those coordinates.

## 1. Tree

A translation campaign's repository, as [`versioning`](../versioning/SKILL.md)'s Repositories
section names it, is laid out as:

```text
<repository>/
├── Cargo.toml          the safe crate, and the workspace
├── src/                the safe crate's modules, as the conventions lay them out
├── tests/              the safe crate's integration test suites
├── ffi/                the raw bindings' generator input and generated bindings, one dir per link unit
├── c/                  the C codebase, the C root, which the safe crate bundles
└── crustify/           the campaign: its settings, artifacts and analysis state
```

The wrappers of the libraries it uses from outside its tree are repositories of their
own, cloned beside it as `../<source>-crustify`, as [`dependencies`](../../planning/dependencies/SKILL.md)
describes.

Every path into the C that the plan records, in `modules.json`, `schedule.json`, the
wavefront configurations and tables and a batch item's `defined_in`, is relative to the C
root, `c/`, so that the plan reads as the C codebase lays itself out. Every other path is
relative to the repository's root.

## 2. Ids

A batch's id is the part of its branch name after `crustify/batches/`:
`wave-<index>/batch-<index>`. It is permanent, since a started wave's index is never
reused or renumbered (see `schedule-schema`), and its entry in `schedule.json` gives the batch's link
unit, module, kind and worklist. A run's id is its batch's id followed by its attempt,
numbered from 1 in the order the batch's runs launch: `wave-3/batch-1/run-2`. A planner
run's is `planner/run-<n>`, numbered among the planner runs, which also names its branch.

A module's dir is its branch's name after `crustify/`: `modules/<link-unit>/<module>`, or
`foundational/<link-unit>/<module>` for a foundational module. A wave that belongs to no
module, such as an audit's, has `waves` in its place.

## 3. Artifact dirs

The campaign's artifacts sit under `crustify/artifacts/`, with one dir per agent run:

```text
crustify/artifacts/                             the campaign
├── build.json                                  the prebuilt variants of the target
├── modules.json                                the module decomposition
├── dependencies.json                           the out-of-tree libraries the target uses
├── schedule.json                               the waves and batches, and their progress
├── dashboard.md                                the campaign dashboard; audit-dashboard.md for an audit
├── planner/run-<n>/                            a planner run
└── <module dir>/wave-<index>/                  a wave's dir: its own records, such as its scans
    └── batch-<index>/run-<n>/                  a run of a batch, a binder's, a translator's or a reviewer's
        ├── task.json                           its input, with the batch and run fields, and its session id
        ├── task.md                             its task message
        └── …                                   the records its run keeps, as the tool skills name them
```

A batch that is run again gets a new run dir, and every attempt keeps its records. A run's
`task.json` names its batch too. The run dir holds
what the campaign keeps of the run: its input, with the backend, billing, model proxy and
arguments it ran under and the session it became, and the artifacts its agent produced.
Its transcript and pricing record are in crustify's home.

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
├── providers/<backend>/              a CLI's config home under API-key billing
├── sessions/<session id>/
│   └── usage.session.json            how a session was priced: its backend, model proxy and rate snapshot
├── rates/<timestamp>.json            the rates `crustify-usage` fetched, kept whenever they changed
└── transcripts/<session id>.jsonl    the agents' transcripts, copied from the CLIs' homes
```

A session's directory is named by its CLI's session id, which its run's `task.json`
records, or, for an agent its host runs inside another session, by the agent's id.

## 6. Scratch

`crustify/tmp/` is gitignored and holds anything residual that is no artifact: downloads,
scratch builds and experiments, intermediate outputs. Residual files go nowhere else in the
repository.

## 7. Reviews

A review batch's findings sit under its reviews dir, `crustify/reviews/<module dir>/<batch id>/`,
such as `crustify/reviews/modules/libgit2/src/libgit2/refs.c/wave-3/batch-1/`, in the repository the review lands in, and a planner
run's plan corrections under `crustify/reviews/planner/`, as
[`reviewing`](../../verification/reviewing/SKILL.md)'s Reports and Plan corrections sections
lay them out.

## 8. Evolution

The campaign's lessons sit in `crustify/LESSONS.md`, and its proposals for Crustify and its
tools under `crustify/evolution/<slug>/`, as [`evolution`](../../crustify/evolution/SKILL.md)
describes.
