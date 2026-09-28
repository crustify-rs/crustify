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

---

## Review mode

### Analysis and lifecycle findings

Verify Wavefront's analysis and lifecycle findings submitted by an earlier run
for your workset. If you find any analysis defect or missing property/lifecycle
primitive, resubmit with a corrected set of findings. File a report describing each
discovered defect in less than 200 words in
`<artifact-dir>/wavefront/<defect-slug>`,
including evidence that proves the previous finding was wrong/incomplete. 