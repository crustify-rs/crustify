<!-- SKILL -->

Before your first command, read wavefront's `README.md`, its `--help`, and the documents
under its `docs/`. Wavefront's repo root is the C root, `c/`: pass `<workdir>/c` as its `repo_root`, so
that every path it reads and reports is below the C root, as the plan records them.

Each section below augments the how-to section it names, as `<how-to> › <section>`.

## items/binding › Item analysis

Leverage the repo-wide Wavefront configuration prepared by the orchestrator
at `crustify/wavefront/configs/wavefront-config.json` to emit queries that will
assist you in performing the analysis of your workset's items.

Submit your findings using Wavefront's `--update` CLI flag and query them later if
you need to consult these findings again.

Before binding a type-erased parameter or field, look it up in the campaign's T3
`crustify/wavefront/t3/chased_casts.csv`: an `erased_arg` / `erased_field` row names the
type it holds, and a `base_derived` row the base a type is reached through. Bind to that
type rather than to a raw pointer. Instances of a generator in `type_generators.csv`
share one generic plus per-instance aliases.

---

## items/binding › Type route › Surface

Read `docs/type-lifecycle.md` beside Wavefront's README for how to identify a type's lifecycle
primitives, and submit your findings through the CLI's `--update`.

---

## items/binding › Symbol route › Lifecycle strategies

The planner submitted each foundational item's lifecycle role to the ownership store:
query it for every item of your batch. Read `docs/type-lifecycle.md` beside Wavefront's
README for how lifecycle primitives are identified, and correct a role that the item's
body contradicts through the CLI's `--update`, naming the correction in your commit
message.
