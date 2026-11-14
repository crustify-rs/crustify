# Auditing a Rust crate

Point Crustify at your crate, and it looks for the bugs that your tests miss: first of
all, undefined behavior that your users can reach from safe code. It works on any Rust
repository, and it suits a crate that wraps a C library best.

To translate C instead, see [Translating C to Rust](translate.md).

## Why audit with Crustify

- **You choose what it hunts for.** Each objective targets one class of bug:

  | objective | what it finds in your crate |
  |---|---|
  | `ub` | undefined behavior reached from your safe API, from your unsafe API within its documented obligations, or by C through your exports |
  | `contracts` | `# Safety` obligations and `// SAFETY:` justifications that can be broken |
  | `equiv` | a safe wrapper that behaves differently from the C that it binds |
  | `logic` | behavior that departs from the library's documented specification |
  | `unsafety`, `ergonomics`, `misc` | API that need not be unsafe, API that is harder to use than it needs to be, and any other defect |
  | `test-adequacy` | gaps in your tests, which it fills with new tests |

- **You get a reproducer, not a suspicion.** A finding reaches you only when a small Cargo
  package triggers Miri, ASan/UBSan, TSan, MSan or BorrowSanitizer through your public
  API. A reproducer for your safe API carries `#![forbid(unsafe_code)]`. You rerun it with
  one command and see the sanitizer's trace yourself.
- **You do not coordinate the work.** The assistant reads your crate, orders its code by
  risk and divides it into worksets. Reviewers take one workset each and run in parallel.
  A last reviewer then reads your crate whole and runs your own tests under Miri and each
  sanitizer that you selected.
- **You read each bug once.** Reports that share a root cause are merged into one, which
  lists every site. Each report says whose bug it is: `soundness` for a defect in your
  crate, `c-bug` for a defect in the C library that you link, and `behaviour` for a defect
  without undefined behavior. Nits go into one note, not into your queue.
- **You can have it fixed.** Add the `fix` task, and the reviewers patch what they
  confirm. Each reproducer becomes a regression test in your own suite. Without `fix`,
  they only report.
- **You can check that a fix holds.** The `revisit` task reruns the reproducers of earlier
  reports on your current revision. A `since` revision limits a new audit to what your
  later commits changed, so you can audit a release, not the whole crate again.
- **You decide what leaves your machine.** An audit sends, posts and files nothing. For a
  bug that belongs to another project, it writes a short disclosure draft and first checks
  that project's tracker for a duplicate or a fix. You send the draft, or you do not.
- **You set the budget.** You give a maximum spend in USD, and the audit stops within it.
  The dashboard tells you what it spent and what it did not get to.

## How to

### 1. Prepare the environment

Use the Docker image, which holds the agent CLIs, Miri and the sanitizer toolchains.
[`templates/docker/README.md`](../templates/docker/README.md) describes how to build it and
start a container. Mount your crate's checkout as `/target`.

To run without Docker, install Crustify as the [README](../README.md#installation)
describes. The audit installs the instruments that it needs during its setup.

### 2. Answer the settings

Copy [`templates/audit/CRUSTIFY.template.md`](../templates/audit/CRUSTIFY.template.md) to
`crustify/CRUSTIFY.md` in your crate's checkout and fill it in. Four answers are mandatory:

| setting | what it decides |
|---|---|
| `source` | your crate and the revision to review |
| `tasks` | whether to hunt for new defects (`audit`), rerun earlier reports (`revisit`), and patch what is confirmed (`fix`) |
| `max-spend` | the maximum spend on this crate, in USD |
| `review-agent`, `billing` | the agent CLI, its model and how it is paid for |

The optional answers select the review objectives, the instruments, the batch size and
whether disclosure drafts are written. Each has a default. If you skip the file, the
assistant asks the same questions in the session.

### 3. Start the audit

Open the audit assistant in your crate's checkout:

```bash
claude --plugin-dir /path/to/crustify --agent crustify:assistant-audit
```

Tell it to start the audit. It presents a brief for your approval before it changes
anything. To run without a terminal, pass the instruction with `-p`, as the Docker README
shows; a headless run needs every mandatory answer.

### 4. What the audit does

1. **Setup.** It builds your crate once for each selected sanitizer and records which C
   library and version each build links.
2. **Scope.** It reads your crate and orders its code by risk. Code where the safe API
   reaches `unsafe` code or C with values, lifetimes or threads that a caller controls
   comes first.
3. **Review waves.** It divides the scope into worksets of about 500 lines. One reviewer
   takes each workset and files a report and a reproducer for every finding that it
   confirms. The reviewers of a wave run in parallel.
4. **Crate pass.** A last reviewer reads your crate whole, for what no workset shows alone,
   and runs your own tests under Miri and each selected sanitizer.
5. **Consolidation.** It merges the reports that share a root cause, checks each
   reproducer and checks each disclosure draft against the upstream tracker.

### 5. Read the results

Everything lands on the working branch, `crustify/devel`, under `crustify/`:

| path | holds |
|---|---|
| `artifacts/audit-dashboard.md` | the findings, one row per root cause, with the scope, the spend and what was not reviewed |
| `reviews/waves/<wave>/<batch>/<objective>/<slug>/report.md` | one finding: its class, evidence, conditions and the command that reruns it |
| the same directory | the reproducer, a standalone Cargo package, and `disclosure.md`, the draft |
| `reviews/notes.md` | what is not worth a report: nits and unproven candidates |

Each report names its class. `soundness` is a defect in your crate. `c-bug` is a defect in
the C library that your crate links, which goes to that library's maintainers.

### 6. Decide what to send

Read a draft and rerun its reproducer before you send it. Each draft records whether the
defect is already reported or fixed upstream, so that you do not file a duplicate.

The assistant then asks whether the shipping branch, `crustify/main`, should advance to
`crustify/devel`. It moves that branch only with your approval.

### 7. Come back later

A later session in the same checkout resumes the audit. To check earlier reports after
upstream fixes land, answer `tasks` with `revisit`: the audit reruns their reproducers and
hunts for nothing new.

## Reference

- [`audit-workflow`](../skills/workflows/audit-workflow/SKILL.md): the whole procedure
- [`reviewing`](../skills/verification/reviewing/SKILL.md): the review objectives
- [`reviewing-reports`](../skills/verification/reviewing/reports/SKILL.md): reports,
  reproducers and disclosure drafts
- [`templates/audit/BARE.md`](../templates/audit/BARE.md): the ablation control, one bare
  agent given only the task
