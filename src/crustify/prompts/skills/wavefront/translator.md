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

---

## items/porting › Surface

Read `docs/type-lifecycle.md` beside Wavefront's README for how to identify a type's lifecycle
primitives, and submit your findings through the CLI's `--update`.
