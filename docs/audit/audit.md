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
crustify /path/to/repo --settings /path/to/CRUSTIFY.md --model anthropic/claude-opus-5
```

Fill in [`CRUSTIFY.template.md`](../../templates/audit/CRUSTIFY.template.md) first; a
headless run needs every mandatory answer. Rerunning the command resumes the audit, and
`--task-only` runs the ablation control described in
[`BARE.md`](../../templates/audit/BARE.md).

## Objectives

| task objective | reviewer objectives |
|---|---|
| `audit` | `ub`, `contracts`, `equiv` when `equivalence` is selected, and `disclose` |
| `revisit` | `revisit` and `disclose`, over the reports the task names or every report filed so far |
| `fix` | adds `fix` to the batches of `audit` and `revisit` |

A task selects `audit`, `revisit` or both, and `fix` optionally.

Without `fix`, reviewers change nothing but their reviews dirs.

## Batches

An audit's review batches carry `modules`, the source files and directories of the crate a
reviewer covers. A module too large for one batch is split by naming the types, each with
its fields and inherent impls, the trait impls (`Drop for Repository`), and the free
functions each batch reviews in it. The orchestrator
batches the modules that hold ffimap's smells first, around 500 lines of code per batch by
default, give or take a small margin (`id: workload` in the task). Reviewers start from the ffimap
sites in their modules, but do not stop at them. A revisit batch carries the `reports` it
reruns:

```json
{"objectives": ["ub", "contracts", "disclose"], "modules": ["src/frame.rs", {"path": "src/codec.rs", "types": ["Decoder"]}]}
{"objectives": ["revisit", "disclose", "fix"], "reports": ["crustify/reviews/<batch id>/ub_safe/<slug>"]}
```

[`task.md`](../translate/schemas/task.md) gives the fields, and
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

- [Audit assistant prompt](../../src/crustify/prompts/audit-assistant.md)
- [Reviewer prompt](../../src/crustify/prompts/reviewer.md)
