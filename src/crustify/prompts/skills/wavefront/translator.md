<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Workflow - base

The following steps augment your base workflow.

### 1. Item analysis

Leverage the repo-wide Wavefront configuration prepared by the orchestrator
at `crustify/wavefront/configs/wavefront-config.json` to emit queries that will
assist you in performing the analysis of your workset's items.

Submit your findings using Wavefront's `--update` CLI flag and query them later if
you need to consult these findings again.

---

## Workflow - type route

The following steps augment your workflow for a type route.

### 1. Surface

Leverage Wavefront's `--schema` CLI flag to get hints on identifying a type's lifecycle
primitives and submit your findings through the CLI's `--update`.

---

## Workflow - symbol route

The following steps augment your workflow for a symbol route.

### 3. Raw lifetime strategies

Leverage Wavefront's `--schema` CLI flag to get hints on identifying raw lifecycle
primitives for void and string and submit your findings through the CLI's `--update`.
