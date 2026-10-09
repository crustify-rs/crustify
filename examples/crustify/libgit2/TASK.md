# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `https://github.com/libgit2/libgit2.git`,
     `ddf3b5c85d86a389330b1d1dd90f08f60ae05fe4`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `wrap`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: named functions and types, as three sub-campaigns run in this order:
     - `import-type-closure`: the whole imported type and callback closure of `src/`,
       in dependency order;
     - `import-symbols-l0-l2`: the imported functions and globals reached by target
       layers L0 through L2 of `src/`;
     - `god-objects`: `git_indexer`, `git_packbuilder` and `git_repository` in
       `src/`, including their transitive closure.

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: ask me, showing the supported providers and models; `api` billing

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: `no`

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `no`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: defaults except `max-types: 1`; parallelism is orchestrator's choice

8. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: not applicable

## Autonomy (if question 6 is answered `no`)

9. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
   - Answer: `no`; Phase 1 is pre-approved
10. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: `no`
11. **Should I wait for your approval between sub-campaigns?** (`id: gates.sub-campaign`)
    - Answer: `yes`, before promoting each sub-campaign branch
12. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: `not applicable`

# Benchmark recording questions

13. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `/target/crustify/results.md`, standard template

# Additional instructions

## Setup

Run Phase 1 end to end. Pre-authored `build.json` and `wavefront-config.json` sit beside
this task in `/opt/crustify/examples/crustify/libgit2/` and may be copied from there.
Emit `subsystems.json` after the campaign-wide oracle target is populated. Skip
toolchain installation when the required tools are already installed.

## Selection and recording

The orchestrator chooses the internal waves, reports each dry-run plan, and waits for
approval before spending on or promoting the next sub-campaign.

After each sub-campaign, price the batches' `translator.usage.json` records with
`crustify cost`, measure the sub-campaign branch's diff, and run
`crustify scan-unsafe <workdir> --json` over the sub-campaign tip. Derive cost
from token counts, never from provider-reported dollars.
