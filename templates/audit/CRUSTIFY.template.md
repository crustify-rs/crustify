Fill in every mandatory answer before a headless run.
Optional answers may be left unresolved: each then takes its default.

The audit files, posts and sends nothing upstream, whatever the answers: its reports,
reproducers and disclosure drafts stay in the repository for you to send.

# Campaign

**Which campaign is this?** (`id: campaign`)
- Answer: `audit`

**Which crate and revision should this audit review?** (`id: source`)
- Answer: `<repository URL or local path>, <commit or tag>[, since: <earlier commit or tag>]`
- With `since`, only what the crate's commits after that revision changed is reviewed.

# Mandatory questions

## Audit

1. **Should the reviewers hunt for new defects, revisit reports an earlier audit
   filed, or both, and should they fix what they confirm?** (`id: tasks`)
   - Answer: `<any of: audit, revisit, fix>`, with `audit`, `revisit` or both
   - `audit` hunts for new defects in the crate.
   - `fix` patches what `audit` confirms and what `revisit` still reproduces;
     without it, reviewers only report.
   - `revisit` hunts nothing new: it reruns the reproducers of the reports an
     earlier audit filed, which is what you want after a fix lands or an
     instrument that can now decide one is added. Name the reports, or leave
     them to the assistant to take every report filed so far.
2. **What is the maximum spend on this crate, in USD? It covers the reviewers, the
   assistant's own sessions and any evolution review. No reviewer launches that the
   remaining budget is not expected to cover, a reviewer still running when the total
   reaches it is stopped, and the dashboard records the spend and what was left
   unreviewed.** (`id: max-spend`)
   - Answer: `<USD>`
3. **Which agent CLI should the reviewers use, with which of its arguments?**
   (`id: review-agent`)
   - Answer: `<claude | codex>[, proxy: openrouter][, args: <the CLI's own
     arguments, such as --model opus>]`
4. **Which billing mode should agentic stages use?** (`id: billing`)
   - Answer: `<api | subscription>`

# Optional questions

## Review

5. **Which objectives should the reviewers review for? By default, every one that
   applies to the crate.** (`id: review-objectives`)
   - Answer: `<all | any of: ub, contracts, equiv, logic, unsafety, ergonomics, idiom,
     conventions, misc, test-adequacy>`
   - `ub`: undefined behaviour reached from the safe API, from the unsafe API within its
     documented obligations, or by C through the crate's exports.
   - `contracts`: `# Safety` obligations and `// SAFETY:` justifications that can be broken.
   - `equiv`: drift between the safe wrapper and the C it binds; needs the `equivalence`
     instrument.
   - `logic`: behaviour that departs from the library's documented specification.
   - `unsafety`, `ergonomics`, `misc`: API that need not be unsafe, API that is harder to
     use than it needs to be, and any other defect; reported together in one note.
   - `idiom` applies to a crate ported from C, and `conventions` to one Crustify generated.
   - `test-adequacy` is run only when named: it adds tests to the crate's own suites.
   - `revisit` and `fix` are selected by `tasks`, and disclosure drafts by `disclosure`.

6. **Which instruments should the reviewers prove findings with? By default, every one
   the toolchain supports.** (`id: instruments`)
   - Answer: `<all supported | miri | asan/ubsan | bsan (borrowsanitizer) | msan (memorysanitizer) | tsan (threadsanitizer) | equivalence | and-separated combination>`
   - `miri`: Rust-side memory, value-validity, alignment, aliasing, intrinsic,
     and data-race UB in code Miri can execute.
   - `asan/ubsan`: native out-of-bounds, lifetime/free, pointer/alignment,
     integer/shift, and invalid runtime-value UB in executed instrumented code.
   - `bsan`: Tree Borrows aliasing and pointer invalidation across Rust and
     foreign code.
   - `msan`: use of uninitialized memory, including buffers and struct tails a
     foreign initializer left partly unwritten. Needs the standard library
     rebuilt (`-Zbuild-std`) and the foreign code instrumented too; anything
     uninstrumented reads as uninitialized and reports falsely.
   - `tsan`: data races across Rust and foreign threads, and unsynchronized use
     of types whose `Send`/`Sync` is asserted by hand. Reports only the
     interleavings that actually run.
   - `equivalence`: functional drift between the safe wrapper and the C API it
     binds, decided by a failing assertion rather than a sanitizer.
   - `msan` and `tsan` each need their own build and cannot share a binary with
     `asan/ubsan`, so selecting them costs an extra build.

7. **Should a crate pass close the audit? It reviews the crate whole, across the
   batches, and runs the crate's own tests under Miri and each selected sanitizer.**
   (`id: crate-pass`)
   - Answer: `<yes | no>`
   - By default: `yes`.

8. **How many reviewers should run at once?** (`id: parallelism`)
   - Answer: `<assistant's choice | N>`
   - By default: the assistant's choice, within what the maximum spend allows.

9. **What batch caps should the reviewers use?** (`id: workload`)
   - Answer: `<defaults | max-loc: N>`
   - Default: around 500 lines of code per batch, a type counted with its impls; a
     small margin either way is allowed.

10. **May deterministic tools, such as ffimap, be run for hints? Their output only
    orients the reading of the crate and cross-checks it: the scope and its priority
    always come from the crate's source, and the audit runs the same without them.**
    (`id: tool-hints`)
    - Answer: `<yes | no>`
    - By default: `yes`, where the tool is installed and runs.

## Reporting

11. **Should a disclosure draft be written for each finding worth reporting?**
    (`id: disclosure`)
    - Answer: `<drafts | none>`
    - By default: `drafts`. A draft is never sent or filed for you.

12. **Before a draft is written, should the upstream tracker and the latest release and
    default branch be checked for a duplicate or a fix? The search sends only generic
    technical terms, such as an API's name.** (`id: upstream-check`)
    - Answer: `<yes | no>`
    - By default: `yes`. With `no`, nothing queries the project's tracker, and each draft
      says it is unchecked.

13. **Where and in what format should the dashboard be recorded? By default, at
    `crustify/artifacts/audit-dashboard.md`, from `templates/audit/dashboard.template.md`.**
    (`id: dashboard`)
    - Answer: `<default | <dashboard path>, <templates/audit/dashboard.template.md | custom template>>`

## Evolution

14. **How far may the audit evolve Crustify and its tools from what it exposes? Agents
    file proposals and record the target's lessons; fixes and improvements land, once
    another agent has reviewed them, on a working branch of each component that is the
    audit's own, and reach the component's `devel` only with your approval.**
    (`id: evolution`)
    - Answer: `<off | propose | repair | evolve>`
    - `propose`: proposals and lessons only. `repair`: also fixes of defects. `evolve`: also
      improvements and new tools. You are asked to take the working branches into `devel`
      at the audit's end. A change to what judges the work, the
      protected paths the `evolution` skill lists, waits for your approval, as that skill's
      Autonomy section describes.
    - By default: `repair`. An evolution review counts against the maximum spend.

## Commits

15. **Which git identity should the campaign's commits carry: an author, and any
    co-authors? By default, Crustify's own, `crustify <crustify@berkeley.edu>` (the
    GitHub account `crustify-ai`), as the author, with no co-author.** (`id: identity`)
    - Answer: `<default | author: Name <email>[, co-authors: Name <email>, ...]>`

## Additional instructions

Unless otherwise stated, match the structure of the given dashboard exactly.

If the user provided a centralized audit tracker at `/opt/crustify-audit-tracker`,
then copy into it all the artifacts that are not gitignored from
`<target repo>/crustify/reviews/` and `<target repo>/crustify/artifacts/`
into `<tracker>/targets/<target>/`
and record the dashboard in the tracker's aggregate `README.md`.
