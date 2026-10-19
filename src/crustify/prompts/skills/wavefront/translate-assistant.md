<!-- SKILL -->

Before your first command, read wavefront's `README.md`, its `--help`, and the documents
under its `docs/`.

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


---

### For Phase 2: Translation

#### 2. Launch preparations

##### Waves and batches

Additionally symlink the CodeQL DB files from `crustify/wavefront/codeql/` and wavefront
`.cache` after forking the worktree for a batch.