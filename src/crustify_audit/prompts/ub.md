Audit the Rust crate in `{workspace}` for undefined behavior reachable from
safe code, and -- when `equivalence` is among your instruments -- for
functional drift between the safe wrapper and the C library it binds. The
repository root is the subject; locate the Rust within it yourself.

## Objective

`{objective}`:

- `audit`: investigate and report; do not modify the target.
- `audit+patch`: investigate, report, and repair confirmed findings.
- `patch`: repair the confirmed advisories named in your workset, or every
  advisory when the workset is omitted; do not hunt for new ones.
- `revisit`: re-investigate the leads named in your workset; do not hunt for
  new ones and do not modify the target.

## Workset

{workset}

## Instruments

{instruments}

For an auditing objective, confine the hunt to defects that one of these
instruments can demonstrate. A confirmed finding must be demonstrated by at
least one of them. The bug-class lists are the hunt scope: do not spend the run
on other classes merely because they are also defects.

If the target ships its own sanitizers because the selected ones structurally
cannot run against it -- the Linux kernel's KASAN, KMSAN, KCSAN and kernel
UBSAN -- use those, and record them under the canonical name they implement.

Before sanitizer work, look in
`{workspace}/crustify/audit/builds/<instrument>/` for the prepared build, using
`asan-ubsan` for `asan/ubsan`. When a matching build exists, reuse it and build only the
reproducer harness. If it is missing or incompatible, document that before
rebuilding and do not report a clean result.

## Audit record

Use `{workspace}/crustify/audit/`:

- `leads/`: one Markdown file for every candidate you investigate, including
  candidates you clear.
- `advisories/`: one directory per confirmed bug with same stem containing
  the reproducer and a `report.md` with the advisory.
- `scratch/`: disposable investigation files.

Read existing leads and advisories first. Do not duplicate completed work.

## Evidence

A finding is confirmed only when safe code demonstrates the defect against the
real audited crate. Write a minimal reproducer that depends on that crate and
calls its public API without using `unsafe`.

For a sanitizer or Miri instrument, the reproducer must trigger that instrument.

For `equivalence`, the reproducer is instead an assertion-based test that calls
the safe wrapper and the C entry point it binds on equivalent, independently
owned inputs and asserts on the observable result: return value, error,
out-parameters, buffers, callback trace, and state after the sequence. The
assertion must FAIL against the crate as it stands, and the test must not
require a sanitizer build to fail. Single calls are the floor: prefer a
multi-call sequence that builds state on both sides and asserts at each step,
since a wrapper that agrees call by call often diverges once state accumulates.

Drift is only a defect when it is unintended. Before filing a drift advisory,
check the crate for evidence that the divergence is deliberate: a doc comment,
a `CHANGELOG` entry, a named test asserting the new behavior, or a commit
message explaining it. Where the crate documents the divergence, or corrects a
C defect on purpose, record it as a LEAD naming the evidence you found and the
behavior on both sides -- never as an advisory. Where you cannot tell, the
finding is a lead: say what evidence would settle it.

Store a confirmed reproducer in `advisories/<name>/` with everything needed to
run it from a clean checkout. The advisory must identify the safe path to the
defect and include the exact command and the relevant instrument output or
assertion failure. If you cannot produce this evidence, record the result as a
lead, not an advisory.

## Revisit

Only when your objective is `revisit`. Your workset names lead files, not source
files. A lead is a question an earlier run could not settle, and your job is to
settle it. For each lead you manage to demonstrate -- a sanitizer crash, or a
failing equivalence assertion -- promote it to an advisory and delete the lead.
A lead recording deliberate drift stays a lead: settling it means confirming
the divergence is still intended, not promoting it.

## Repair

Only when your objective includes patching. Under `audit`, an advisory is
finished when it is written.

Under `patch`, repair only the advisory directories named in the workset. An
omitted workset means every existing advisory. Do not substitute a different
advisory merely because its affected source is nearby.

Work in a git worktree, never in the checkout. Follow the repository's
contributor instructions, make the smallest sound fix with focused regression
tests, run the relevant project checks, and rerun the original reproduction.
Commit the repair in the worktree. Do not merge, do not push, and do not remove
the worktree. Record the worktree, branch, commit, commands, and results in the
advisory.

## Avoid leaks

Do not include any API keys in core dumps or any other reproducer artifacts
as we might be making the audit tree open source.

## Draft disclosure notice

Read the affected repo's conventions for disclosing security / UB issues and
draft a disclosure notice that the user could send outside the box without
further adjustments. If it should be first sent via email, use an email-friendly
format, and name the maintainers to which it should be disclosed. Keep disclosure
notices under 450 words. Only offer to provide fix patches or PRs when your objective
included that, otherwise we only disclose. Mentioned reproducers are only provided
on request but add in the disclosure a small snippet and the santizer crash.

Add the following note to the disclosure: `Found by [Crustify](https://github.com/crustify-rs/crustify),
an experimental UB/soundness auditing agent developed at UC Berkeley and running on <model name>,
then manually reviewed and independently reproduced.`
