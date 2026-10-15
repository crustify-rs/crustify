# Audit campaigns

An audit campaign hunts undefined behavior reachable from safe code in a Rust repository,
especially a crate that wraps C, and, when the `equivalence` instrument is selected,
functional drift between the safe wrapper and the C library it binds. It needs no earlier
Crustify campaign: the target is any repository.

An audit runs the same reviewers a translation campaign does. Its orchestrator plans the
audit, prepares the instrumented builds and spawns the reviewers, and each reviewer files
a report and a reproducer for every finding it confirms.

## Running one

```sh
crustify audit /path/to/repo /path/to/TASK.md --model anthropic/claude-opus-5
```

Fill in [`TASK.template.md`](../../templates/audit/TASK.template.md) first; a
headless run needs every mandatory answer. Rerunning the command resumes the audit, and
`--task-only` runs the ablation control described in
[`BARE.md`](../../templates/audit/BARE.md).

## Objectives

| task objective | reviewer objectives |
|---|---|
| `audit` | `ub`, `equiv` when `equivalence` is selected, and `disclose` |
| `revisit` | `revisit` and `disclose`, over the reports the task names or every report filed so far |
| `fix` | adds `fix` to the batches of `audit` and `revisit` |

A task selects `audit`, `revisit` or both, and `fix` optionally.

Without `fix`, reviewers change nothing but their reviews dirs.

## Batches

An audit's review batches carry `modules`, the source files and directories of the crate
a reviewer covers, instead of a translation's `items`. A revisit batch carries the
`reports` it reruns:

```json
{"objectives": ["ub", "equiv", "disclose"], "modules": ["src/frame.rs", "src/codec/"]}
{"objectives": ["revisit", "disclose", "fix"], "reports": ["crustify/reviews/<batch id>/ub_safe/<slug>"]}
```

[`batch.md`](../translate/schemas/batch.md) gives the fields, and
[`layout.md`](../translate/howto/layout.md) the branches and artifact dirs an audit's
review waves use.

## Instruments

Each selected sanitizer is a variant of `crustify/artifacts/build.json`, which the orchestrator
prepares before the first review wave; the reviewers use only those variants. Miri and
`equivalence` need no build. [`testing.md`](../translate/howto/testing.md) gives the bug
classes each sanitizer covers.

## Spending

The task sets a maximum spend. Before each launch, the orchestrator prices every usage
record the audit has written with `crustify cost`, and once the total reaches the
maximum it launches no further reviewers.

## Output

Each reviewer files its findings under its reviews dir, `crustify/reviews/<batch id>/`, and
lands them on its review wave's branch. With `disclose`, every finding carries a
`disclosure.md` ready to send to the project's maintainers. The orchestrator fills the
audit's dashboard from
[`dashboard.template.md`](../../templates/audit/dashboard.template.md).

## Reference

- [Audit orchestrator prompt](../../src/crustify/prompts/audit-orchestrator.md)
- [Reviewer prompt](../../src/crustify/prompts/reviewer.md)
