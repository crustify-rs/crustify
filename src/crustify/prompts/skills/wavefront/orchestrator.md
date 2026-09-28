<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Workflow

The following steps augment your base workflow.

### For Phase 1: Setup

#### 1. Provision dependencies

- Install CodeQL if it's not already installed and add the following artifacts to the
  tree's gitignore: `wavefront/codeql` and `wavefront/.cache`.


#### 2. Artifact tree scaffolding

- Scaffold `crustify/wavefront/` for wavefront-owned artifacts.


#### 3. Prebuilds and test baselines

##### CodeQL setup

- Wavefront requires the CodeQL T1/T2 tables for computing dependencies; emit them after
  creating the target's builds and recording the test baseline; place codeql-owned
  artifacts in `crustify/wavefront/codeql/{t1, t2, ...}`.


#### 4. Subsystem decomposition

##### Configuring `wavefront-config.json`

After subsystem decomposition, emit campaign-wide and per-subsystem
`wavefront-config.json` specs that can be consumed by the wavefront CLI.

Selection rules:

- `impl_files` and `api_headers` seed the implementation graph. - An entity is targeted
  when its definition is in a named file. For an entity without a body, all declarations
  must be in named files. - Headers outside the implementation tree must be named when
  they define target types. - Add a header to `api_headers` only when its implementors are
  in `impl_files`. - Dependencies merely used by the target enter the imported closure. -
  `--api-headers-only` selects declarations published by `api_headers` and does not walk
  bodies. - A struct defined in `api_headers` retains field layout. A forward declaration
  remains opaque. - `targeted` and `imported` describe ownership; `api` describes
  publication. These sets intersect. - `out_of_scope.paths` changes selection.
  `out_of_scope.features` is documentation only.

###### Campaign-wide

- Configure a campaign-wide `crustify/wavefront/configs/wavefront-config.json` that every
  translator agent will resolve its queries through.

###### Per subsystem

- To get exact counts when authoring `subsystems.json`, configure for each subsystem a
  `crustify/wavefront/configs/<link-unit>/<subsystem>/wavefront-config.json`.

- Its `impl_files` and `api_headers` must be exact subsets of the campaign-wide
  configuration, and must mirror the subsystem's assigned sources in `subsystems.json`.

- Verify the authored configurations against wavefront's CLI.

#### 5. Planning

- Leverage the per-subsystem `wavefront-config.json` when emitting `schedule.json` to form
  dependency-ordered DAGs over link units, subsystems, and type/symbol batches.

- Prefer `--transitive` so the sub-campaign includes the selected surface's in-scope
  producer dependencies. Use an exact non-transitive selection only when those
  dependencies are already satisfied or intentionally excluded.

- Wrap campaigns use `schedule --api-headers-only`.

- Use the established batch caps to limit agent work.

---

### For Phase 2: Translation

### 2. Launch preparations

#### Waves and batches

Additionally symlink the CodeQL DB files from `crustify/wavefront/codeql/` and wavefront
`.cache` after forking the worktree for a batch.