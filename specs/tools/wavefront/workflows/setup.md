# wavefront › workflows/setup

## Provisioning

CodeQL is installed, and wavefront's query pack dependencies with `codeql pack install`
on wavefront's `src/`: extraction fails without them. `crustify/.gitignore` lists
`wavefront/codeql` and `wavefront/.cache`.

## Artifact tree

`crustify/wavefront/` is scaffolded for wavefront's artifacts.

## Baseline

Once the builds and the baseline are recorded, the CodeQL T1/T2 tables wavefront computes
dependencies from are emitted. The CodeQL database is created under
`crustify/wavefront/codeql/` from a traced build of the `plain` configuration in a fresh
scratch dir, with `c/` as its source root, and the tables are extracted into
`crustify/wavefront/codeql/{t1,t2}` through a configuration whose `state_dir` is
`../crustify/wavefront`. That bootstrap configuration sits in `crustify/tmp/`; the
campaign's own configurations are the plan's.
