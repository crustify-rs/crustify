# Campaign layout

A campaign's branches, worktrees and artifact dirs are all derived from the same
coordinates: the campaign id, the link unit, the subsystem, the wave index and the batch
index. Nothing records a path; each name below is spelled from those coordinates.

## Branches

| branch | name | checked out |
|---|---|---|
| campaign | `crustify/campaigns/<campaign-id>` | in the repository's base dir, between subsystems |
| subsystem | `crustify/subsystems/<campaign-id>/<link-unit>/<subsystem>` | in the repository's base dir, while live |
| wave | `crustify/waves/<campaign-id>/<link-unit>/<subsystem>/wave-<index>` | never |
| batch | `crustify/batches/<campaign-id>/<link-unit>/<subsystem>/wave-<index>/batch-<index>` | in its worktree |
| review wave | `crustify/reviews/<campaign-id>/<link-unit>/<subsystem>/wave-<index>` | never |
| review batch | `crustify/review-batches/<campaign-id>/<link-unit>/<subsystem>/wave-<index>/batch-<index>` | in its worktree |

A campaign begun before subsystems were named so has `crustify/subcampaigns/` subsystem
branches; resuming it keeps them.

A wave or review wave branch is the integration branch its batches land on. It is never
checked out: a landing push to a checked-out branch fails, and one to a missing branch
silently creates it.

## Worktrees

Each batch and review batch has its own worktree at `crustify/.worktrees/<its branch name>`.

## Batch ids

A batch's id is the part of its branch name after `crustify/batches/` or
`crustify/review-batches/`: `<campaign-id>/<link-unit>/<subsystem>/wave-<index>/batch-<index>`.
It gives the batch's link unit, subsystem and wave.

## Artifact dirs

Every level of a campaign has an artifact dir under `crustify/campaigns/`:

```text
crustify/campaigns/<campaign-id>/               the campaign: schedule.json, the orchestrator's log
└── <link-unit>/<subsystem>/                    a subsystem
    ├── wave-<index>/                           a wave
    │   └── batch-<index>/                      a batch
    │       ├── batch.json                      the thin batch, written out from schedule.json
    │       ├── <role>.log                      binder, translator or reviewer
    │       └── <role>.usage.json
    └── review-wave-<index>/                    a review wave
        └── batch-<index>/                      a review batch, laid out as a batch
```

Each level also holds its `ffimap.json` once the orchestrator records it. A batch's artifact
dir is what its `--output` names, and holds everything about that batch: its input and the
artifacts its agent produced.

## Reviews

A review batch files its findings under its reviews dir, `crustify/reviews/<batch id>/`, in
the repository the review lands in: one `<slug>` directory per finding, holding its report
and, when it has one, its reproducer, under the sub-directory of the finding's kind.
