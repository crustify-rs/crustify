<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

Each section below augments the how-to section it names, as `<how-to> › <section>`.

## binding › Item analysis

Leverage the repo-wide Wavefront configuration prepared by the orchestrator
at `crustify/wavefront/configs/wavefront-config.json` to emit queries that will
assist you in performing the analysis of your workset's items.

Submit your findings using Wavefront's `--update` CLI flag and query them later if
you need to consult these findings again.

Wavefront does not follow a type-erased pointer through calls. Before binding a
type-erased parameter, query the function's `_comment_agent` for a recorded chain, or
trace it yourself,
to find the type it is read as; bind to that type rather than to a raw pointer when the
chain establishes it.

---

## binding › Type route › Surface

Leverage Wavefront's `--schema` CLI flag to get hints on identifying a type's lifecycle
primitives and submit your findings through the CLI's `--update`.

---

## binding › Symbol route › Raw lifetime strategies

Leverage Wavefront's `--schema` CLI flag to get hints on identifying raw lifecycle
primitives for void and string and submit your findings through the CLI's `--update`.
