# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: the existing checkout mounted at `/target`, at its current checked-out
     revision

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `port`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: orchestrator's choice of bottom-up subsystems under `src/`, stopping after
     at least 10K LoC of C has been ported to native Rust

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: `openai/gpt-5.6-sol, api`

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: `openrouter/anthropic/claude-opus-5, api`, after each wave

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `no`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: `max-types: 2, max-syms: 25, max-loc: 500`, at least 20 fields per type
     batch; parallelism is orchestrator's choice

8. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: `same as translation`

## Autonomy (if question 6 is answered `no`)

9. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
   - Answer: `no`
10. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: `yes`, after setup identifies and proposes the bottom-up subsystem plan
11. **Should I wait for your approval between sub-campaigns?** (`id: gates.sub-campaign`)
    - Answer: `no`
12. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: `no`

# Benchmark recording questions

13. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `/target/crustify/results.md`, standard template

# Additional instructions

- Work in `/target` in place. Do not clone, reset, replace, or discard its existing
  branches or partial `crustify/` translation.
- The campaign is in flight but was interrupted, and this run resumes it (started with
  `--campaign <id>`). Continue from its completed artifacts rather than restarting.
