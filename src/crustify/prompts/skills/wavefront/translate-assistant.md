<!-- SKILL -->

Before your first command, read wavefront's `README.md`, its `--help`, and the documents
under its `docs/`. Wavefront's repo root is the C root, `c/`: pass `<workdir>/c` as its `repo_root`, so
that every path it reads and reports is below the C root, as the plan records them.

## workflows/setup › Provisioning

Install CodeQL if it is not installed, and wavefront's query pack dependencies with
`codeql pack install` on wavefront's `src/`: extraction fails without them. Add
`wavefront/codeql` and `wavefront/.cache` to `crustify/.gitignore`.

## workflows/setup › Artifact tree

Scaffold `crustify/wavefront/` for wavefront's artifacts.

## workflows/setup › Baseline

Once the builds and the baseline are recorded, emit the CodeQL T1/T2 tables wavefront
computes dependencies from. Create the CodeQL database under `crustify/wavefront/codeql/`
from a traced build of the `plain` configuration in a fresh scratch dir, with `c/` as its
source root, then extract the tables into `crustify/wavefront/codeql/{t1,t2}` through a
configuration whose `state_dir` is `../crustify/wavefront`. The planner writes the campaign's own configurations; a
bootstrap configuration for the extraction belongs in `crustify/tmp/`.

## versioning › Lifecycle › Batches

The CodeQL database and tables under `crustify/wavefront/codeql/`, and wavefront's
`.cache`, are gitignored state every batch needs: symlink them into each batch's worktree
after forking it.
