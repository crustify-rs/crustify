# Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work. Each commit
message ends with a `Batch: <batch id>` trailer, which ties the commit to the batch's
artifact dir, `crustify/artifacts/<batch id>/`, through rebases.

The landing operation is a local push through the Git common directory:

```bash
git push "$(git rev-parse --git-common-dir)" HEAD:refs/heads/<integration branch>
```

`git update-ref` is no substitute: its compare-and-swap form makes the ref update atomic,
but does not enforce that the new commit descends from the expected old commit.

On a non-fast-forward rejection, the batch:

1. rebases only its own branch onto the current integration branch;
2. reruns its validation; and
3. retries the fast-forward.

The integration branch is never reset, force-updated or moved backward, and nothing is
pushed to a remote. The worktree stays after landing; removing it is the orchestrator's job.

## Dashboard rows

In a translation campaign, a batch records itself in the campaign dashboard,
`crustify/artifacts/dashboard.md`, in its last commit. It fills every cell it can measure
on the tree it lands:

- under the kind of each of its items, its rows in the kind's `Batches`, tests and
  `Batches: safety audit` tables, and for a review batch in
  `Batches — review: PoC + reports`, each placed in subsystem, wave and batch order under
  its `pass`, and those tables' `Σ` rows; and
- the `Coverage stats` table and the Overview's LoC line, at the tree it lands.

Its rows are measured against the integration branch tip it was rebased onto, coverage
as the testing instructions' Coverage section measures it. A batch cannot see its own
cost, tokens and wall, nor whether the orchestrator accepts its PoCs, so it leaves those
cells, the per-unit costs and their `Σ` cells to the orchestrator, which fills them once
the batch's agent has ended. A rebase that conflicts in the dashboard keeps every row both
sides added, and the batch measures its cells again, `Σ` rows included, when it reruns its
validation.
