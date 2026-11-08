
Fill in as many answers as you want before starting Crustify. It will ask only
for campaign decisions that remain unresolved.

# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `<repository URL>, <commit or tag>`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: campaign`)
   - Answer: `<port | wrap>`

3. **What should this campaign target: a named subset of modules, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: `<named modules | named functions/types | whole target |
     assistant's choice>`

4. **Which agent CLI and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: `<claude | codex>, <subscription | api>[, proxy: openrouter][,
     args: <the CLI's own arguments>]`, e.g. `claude, subscription, args:
     --model opus --effort high`.
     - `claude` is Claude Code, `codex` is Codex; each runs its own default
       model unless `args` names another, in its own syntax (`--model opus`,
       `-m gpt-6-sol`).
     - `subscription` is the CLI's logged-in account; `api` is an API key from
       the environment.
     - `proxy: openrouter` sends the CLI's requests through OpenRouter, with
       `OPENROUTER_API_KEY`; it needs `api` billing, and Codex needs its model
       named as OpenRouter knows it (`-m openai/<model>`).

5. **Do you want agentic review after translated work lands? If so, which
   agent CLI and billing should perform each review?** (`id: review-agent`)
   - Answer: `<no | claude | codex, subscription | api[, proxy: …][, args: …]>`

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `<yes | no>`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Which agent CLI and billing should plan the campaign, and how many planner runs
   should it make? Each run emits what the plan lacks and corrects what the runs
   before it committed.** (`id: plan-agent`)
   - Answer: `<claude | codex, subscription | api[, proxy: …][, args: …]>, runs: N |
     orchestrator's choice>`
   - By default: the translation agent's, 2 runs.

8. **Should batches and parallelism be capped? Each wave's batches are packed when it
   starts, sized by its items, the agents and the host; a cap bounds every batch, or the
   agents running at once.** (`id: workload`)
   - Answer: `<assistant's choice | any of: max-types: N, max-syms: N, max-loc: N,
     parallelism: N>`
   - By default: no cap.

9. **Should review batches be capped? They are packed larger than translation batches,
   since a reviewer reads landed code rather than writing it.** (`id: review-workload`)
   - Answer: `<assistant's choice | any of: max-types: N, max-syms: N, max-loc: N>`
   - By default: no cap.

10. **Which objectives should review agents review for? By default, every one the
    reviewer offers.** (`id: review-objectives`)
    - Answer: `<all | any of: lifecycle, unsafety, contracts, ub, equiv, internal,
      conventions, misc, coverage, disclose, fix>`
    - Without `fix`, reviewers report and reproduce what they find but patch nothing.

11. **Which sanitizers should the campaign build and test under? By default, every one
    the toolchain supports.** (`id: sanitizers`)
    - Answer: `<all supported | any of: asan-ubsan, msan, tsan, bsan>`
    - Miri needs no build and is always on.

12. **How should the target be configured: which of its build features should be
    enabled or disabled?** (`id: target-config`)
    - Answer: `<default | default, plus: enable X, disable Y | configure flags>`
    - By default: the target's default configuration, with deprecated features disabled.

13. **Should modules that do not depend on each other run concurrently, each on its own
    branch, or should their waves be merged and run one at a time?**
    (`id: module-concurrency`)
    - Answer: `<concurrent | merged>`
    - By default: concurrent, within the scope and as many at once as the host allows.

14. **At which points should the hybrid C-Rust program ship? Shipping advances `main` to
    what the campaign has integrated, with your approval each time: the modules shipped
    are translated, and the C still left is reached only through the wrappers on its
    boundary.** (`id: ship`)
    - Answer: `<after every integrated module | after: <named modules> | once the scope
      is done>`
    - By default: after every integrated module.

## Commits

15. **Which git identity should the campaign's commits carry: an author, and any
    co-authors? By default, Crustify's own, `crustify <crustify@berkeley.edu>` (the
    GitHub account `crustify-ai`), as the author, with no co-author.** (`id: identity`)
    - Answer: `<default | author: Name <email>[, co-authors: Name <email>, ...]>`

## Autonomy (if question 6 is answered `no`)

Answer these approval-gate questions only if question 6 is answered `no`.

16. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
    - Answer: `<yes | no>`
17. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: `<yes | no>`
18. **Should I wait for your approval before integrating each module into the working
    branch?** (`id: gates.module`)
    - Answer: `<yes | no | not applicable>`
19. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: `<yes | no | not applicable>`

# Benchmark recording questions

20. **Where and in what format should the dashboard be recorded? By default, at
    `crustify/artifacts/dashboard.md`, from the standard template.** (`id: dashboard`)
    - Answer: `<default | <dashboard path>, <standard | custom template>>`

# Additional instructions

Unless otherwise stated, preserve the format of the dashboard exactly.

