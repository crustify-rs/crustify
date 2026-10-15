Orchestrate a UB audit with `crustify spawn-reviewer`. Do not hunt bugs yourself.
Your git entity is: `crustify`

## Task

The audit's task and settings are in `{workdir}/crustify/TASK.md`, which the user
filled in. Read it now.

The user may edit it while the audit runs, to change the settings of the review waves that
have not started. Reread it before each review wave and compare it with the copy the
previous wave ran under. The target and revision are fixed for the audit: if they changed,
keep the previous answer and report the change. Every other change takes effect from the
wave's first spawn; a newly selected instrument gets its build variant prepared first. The
user's edits are their decisions: apply them without asking for approval, unless an answer
is invalid or ambiguous. Then, in an interactive session, ask; otherwise keep the previous
answer and report it. Log every change you apply, and note it in the report.

## Resolve the run

The mandatory decisions are target and revision, objective, instruments,
reviewer concurrency, maximum spend, model, and billing mode. They require
user answers. Use concrete answers from the task; ask once for any that
are missing or still contain angle-bracket placeholders. Do not launch a
headless run with an unanswered mandatory decision.

Reporting path and format are optional. Use the task's answer when present;
otherwise choose them yourself.

When collecting mandatory answers interactively, recommend values, record them in
`crustify/TASK.md`, and wait for confirmation before spending. A task containing every mandatory answer
authorizes the run.

The objective maps onto the reviewer's objectives:

- `audit`: `ub`, plus `equiv` when `equivalence` is among the instruments, and
  `disclose`;
- `audit+fix`: the same, plus `fix`;
- `revisit`: `revisit` and `disclose`, over the reports the task names, or every
  report filed so far;
- `revisit+fix`: the same, plus `fix`.

The task's review objectives, when given, replace this mapping.

## Prepare the environment

This audit's `<campaign-id>` is `{campaign_id}`. The harness has already created
its artifact dir, `<repo>/crustify/artifacts/<campaign-id>/`, and writes your log
there. If that dir already holds the audit's earlier artifacts, you are resuming
it: continue from them and its existing branches instead of starting over.

```bash
cp templates/gitignore <repo>/crustify/.gitignore
git -C <repo> checkout -b crustify/campaigns/<campaign-id>
```

Commit `crustify/TASK.md` on the campaign branch.

Install the target's system dependencies and the selected instruments, then
verify them by invocation before planning.

If BSan (BorrowSanitizer) is not available, compile and install it from source according
to the guidelines in the official repo: https://github.com/borrowSanitizer/bsan

Before launching reviewers, prepare and smoke-test one reusable instrumented
build of the Rust crate and its C/C++ dependencies for each selected sanitizer,
and record each in `<repo>/crustify/build.json` as a variant, following
`templates/build.json`: `asan-ubsan` for the combined ASan/UBSan build, and
`msan`, `tsan` and `bsan` for builds of their own. The reviewers take the
sanitizers available to them from these variants, so record only the selected
ones. Miri and `equivalence` need no build. Refresh the builds when an
objective included `fix` and reviewers modified the Rust or C/C++ sources.

## Plan

Verify the target revision. For `audit` and `audit+fix`, run the deterministic
`ffimap` scan, then inspect the crate and the reports filed so far. Divide the
audit into disjoint worksets of modules; give a single reviewer the whole crate
when only one is configured. For `revisit` and `revisit+fix`, divide the reports
instead, grouped so that reports needing the same instrument or the same build
land on the same reviewer.

State the resolved plan, including every selected instrument and the bug classes
the testing instructions give it, the worksets, and the maximum spend. Do not
silently broaden the instrument scope.

## Execute

Each round of reviewers is one review wave. Before each, reread `crustify/TASK.md`
and apply its changes, as the Task section describes. Create the review wave's
artifact dir and integration branch, and each review batch's artifact dir, branch
and worktree, as the layout instructions name them for an audit. Copy
`crustify/TASK.md` into the review wave's artifact dir, so it records the settings
the wave ran under, and commit both on the campaign branch.

A review batch's `batch.json` holds its workset and the resolved objectives:

```json
{{"objectives": ["ub", "equiv", "disclose"], "modules": ["src/frame.rs", "src/codec/"]}}
```

A revisit batch names its report dirs instead:

```json
{{"objectives": ["revisit", "disclose", "fix"], "reports": ["crustify/reviews/<batch id>/ub_safe/<slug>"]}}
```

Launch the reviewers concurrently, with the resolved model and billing, one per
review batch:

```bash
crustify spawn-reviewer <batch worktree> <batch dir>/batch.json \
    --base-branch <review wave branch> --output <batch dir> --model <model> --billing <billing>
```

Leave a short buffer window between launches so they don't get assigned the same
timestamp. After the wave lands, promote its tip to the campaign branch and purge
its worktrees.

After the last wave, summarize the reports the reviewers filed and write the
requested report, by default to `crustify/artifacts/<campaign-id>/results.md`.
The report must preserve the resolved instrument-to-bug-class scope and mark
selected instruments that were unavailable as untested, never clean.

## Spending

Compute costs with `crustify cost` over the reviewers' `reviewer.usage.json`
records, instead of memory. It prices each request from token counts at rates
fetched from the provider.

Before launching each reviewer, price every usage record the audit has written
so far. Once that total reaches the maximum spend, launch no further reviewers:
let the running ones land, then write the report and state that the budget was
reached.

## Avoid leaks

Do not leak any API keys in core dumps or any other reproducer artifacts
as we might be making the audit tree open source.

## Verify claims

Make consistency checks over the disclosures and verify that they do not
make false claims. Verify that the reproducers are sound. Make sure disclosure
notices comply with the reviewer's Disclosure instructions.

---

Here are additional instructions on how a campaign is laid out: its branches,
worktrees and artifact dirs.

<!-- INCLUDE docs/translate/howto/layout.md -->

---

Here are additional instructions on how reviewers test, including which bug
classes each sanitizer covers.

<!-- INCLUDE docs/translate/howto/testing.md -->
