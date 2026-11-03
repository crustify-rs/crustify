# wavefront › operations/versioning

## Lifecycle › Batches

The CodeQL database and tables under `crustify/wavefront/codeql/`, and wavefront's
`.cache`, are gitignored state every batch needs: they are symlinked into each batch's
worktree once it is forked.
