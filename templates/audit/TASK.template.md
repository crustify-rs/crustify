
Fill in every mandatory answer before a headless run.
Optional answers may be left unresolved for the orchestrator to decide.

# Mandatory questions

## Audit

1. **Should the reviewers hunt for new defects, revisit reports an earlier audit
   filed, or both, and should they fix what they confirm?**
   - Answer: `<any of: audit, revisit, fix>`, with `audit`, `revisit` or both
   - `audit` hunts for new defects in the crate.
   - `fix` patches what `audit` confirms and what `revisit` still reproduces;
     without it, reviewers only report.
   - `revisit` hunts nothing new: it reruns the reproducers of the reports an
     earlier audit filed, which is what you want after a fix lands or an
     instrument that can now decide one is added. Name the reports, or leave
     them to the orchestrator to take every report filed so far.
2. **How many reviewers should run at once?**
   - Answer: `<N>`
3. **What is the maximum spend, in USD? Once the audit's priced usage reaches
   it, the orchestrator launches no further reviewers.**
   - Answer: `<USD>`
4. **Which backend and model should the reviewers use?**
   - Answer: `<backend, model>`
5. **Which billing mode should agentic stages use?**
   - Answer: `<api | subscription>`
6. **Which instruments should the reviewers hunt with?**
   - Answer: `<miri | asan/ubsan | bsan (borrowsanitizer) | msan (memorysanitizer) | tsan (threadsanitizer) | equivalence | and-separated combination>`
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

# Optional questions

Unanswered optional questions are decided by the orchestrator.

## Review

7. **Which objectives should the reviewers review for? By default, the objective above
   decides: `ub`, `contracts`, `equiv` when `equivalence` is an instrument, and
   `disclose` for `audit`; `revisit` and `disclose` for `revisit`; plus `fix` for `fix`.**
   - Answer: `<default | any of: unsafety, contracts, ub, equiv, internal, misc,
     coverage, revisit, disclose, fix>`

## Reporting

8. **Where and in what format should the dashboard be recorded?**
   - Answer: `<dashboard path>, <templates/audit/dashboard.template.md | custom template>`


## Additional instructions

Unless otherwise stated, match the structure of the given dashboard exactly.

If the user provided a centralized audit tracker at `optcrustify-audit-tracker`,
then copy into it all the artifacts that are not gitignored from
`<target repo>/crustify/reviews/` and `<target repo>/crustify/artifacts/`
into `<tracker>/targets/<target>/`
and record the dashboard in the tracker's aggregate `README.md`.
