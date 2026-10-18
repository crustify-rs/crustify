# Campaign layout

A repository holds one campaign, and its work is cumulative: a later run resumes it and
skips what it already completed. Its branches, worktrees and artifact dirs are all derived
from the same coordinates: the link unit, the subsystem, the wave index and the batch
index. Nothing records a path; each name below is spelled from those coordinates.

## Branches

| branch | name | checked out |
|---|---|---|
| campaign | `crustify/campaign` | in the repository's base dir, between subsystems |
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
| campaign | `crustify/campaign` | in the repository's base dir |
| review wave | `crustify/reviews/wave-<index>` | never |
| review batch | `crustify/review-batches/wave-<index>/batch-<index>` | in its worktree |

## Worktrees

Each batch and review batch has its own worktree at `crustify/.worktrees/<its branch name>`.

## Batch ids

A batch's id is the part of its branch name after `crustify/batches/` or
`crustify/review-batches/`: `<link-unit>/<subsystem>/wave-<index>/batch-<index>`, or
`wave-<index>/batch-<index>` in an audit. It gives the batch's link unit,
subsystem and wave.

## Artifact dirs

Every level of a campaign has an artifact dir under `crustify/artifacts/`:

```text
crustify/artifacts/                             the campaign
├── build.json                                  the prebuilt variants of the target
├── subsystems.json                             the subsystem decomposition
├── schedule.json                               the waves and batches of every subsystem
├── dashboard.md                                the campaign dashboard; audit-dashboard.md for an audit
├── orchestrator-<timestamp>.log                one per orchestrator run
└── <link-unit>/<subsystem>/                    a subsystem
    ├── TASK.md                                 the settings the subsystem ran under
    ├── wave-<index>/                           a wave
    │   └── batch-<index>/                      a batch
    │       ├── batch.json                      the thin batch, written out from schedule.json
    │       ├── <role>.log                      binder, translator or reviewer
    │       └── <role>.usage.json
    └── review-wave-<index>/                    a review wave
        └── batch-<index>/                      a review batch, laid out as a batch
```

An audit's review waves sit directly in the campaign's artifact dir, as
`crustify/artifacts/review-wave-<index>/batch-<index>/`.

Each level also holds its `ffimap.json` once the orchestrator records it. A batch's artifact
dir is what its `--output` names, and holds everything about that batch: its input and the
artifacts its agent produced.

## Scratch

`crustify/tmp/` is gitignored and holds anything residual that is no artifact: downloads,
scratch builds and experiments, intermediate outputs. Residual files go nowhere else in the
repository.

## Reviews

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`, in
the repository the review lands in: one `<slug>` directory per finding, holding its report
and, when it has one, its reproducer, under the sub-directory of the finding's kind.

A planner that amends an earlier plan files its findings the same way under
`crustify/reviews/planner/`: `subsystems/` for `subsystems.json` and `schedule.json`, and
one sub-directory per skill artifact it amends (wavefront's `chased-casts/` and
`type-generators/`).
