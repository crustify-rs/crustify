<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

Each section below augments the how-to section it names, as `<how-to> › <section>`.

## binding › Item analysis

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

## binding › Type route › Surface

Leverage Wavefront's `--schema` CLI flag to get hints on identifying a type's lifecycle
primitives and submit your findings through the CLI's `--update`.

---

## binding › Symbol route › Raw lifetime strategies

Leverage Wavefront's `--schema` CLI flag to get hints on identifying raw lifecycle
primitives for void and string and submit your findings through the CLI's `--update`.
