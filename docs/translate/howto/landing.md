# Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work.

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
