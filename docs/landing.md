# Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work. A commit carries
no trailer: what ties it to its batch is the batch's record of what it landed.

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

Once the push succeeds, the commits it landed, those between the integration branch's
tip it was rebased onto and its own `HEAD`, oldest first, are recorded in `landed.json` in
the run's artifact dir:

```json
{"branch": "crustify/waves/wave-7", "commits": ["3f2a9c1", "8be04d7"]}
```

The file stays out of the landed commits, which cannot name themselves. They become the
batch's `commits` in `schedule.json`.

The integration branch is never reset, force-updated or moved backward, and nothing is
pushed to a remote. The worktree stays after landing, until it is purged as [`layout.md`](layout.md)'s Lifecycle section describes.
