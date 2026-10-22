# Landing

A batch lands its commits on the integration branch it was given, which is never checked
out. Before committing, the diff is checked to contain no unrelated work. A commit carries
no trailer: what ties it to its batch is the batch's branch, whose tip it is or precedes.

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

Every landing is a fast-forward, so an integration branch is linear, and each batch's
commits are one unbroken run of it, ending at its branch's tip and starting after the wave
base or the tip of the batch that landed before it:

```bash
git rev-list --reverse <batch branch> --not <wave base> <the wave's other landed batch branches>
```

They become the batch's `commits` in `schedule.json`.

The integration branch is never reset, force-updated or moved backward, and nothing is
pushed to a remote. The worktree stays after landing, until it is purged as [`layout.md`](layout.md)'s Lifecycle section describes.
