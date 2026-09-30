# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `https://github.com/openssl/openssl`,
     `2924476b5591e691e904c4baf57894c526c4b8de`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `wrap`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: a subset of the libcrypto public API that I select during the live
     session; derive implementation paths from the libcrypto build definition and
     headers from its public headers; exclude libssl

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: `openai/gpt-5.6-sol, api`

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: ask me for the model and at which milestones

6. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: ask me

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

7. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: defaults except `max-types: 2`; parallelism is orchestrator's choice

8. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: ask me; recommend 3x the translation caps

## Autonomy (if question 6 is answered `no`)

9. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
   - Answer: ask me if autonomy is declined
10. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: ask me
11. **Should I wait for your approval between sub-campaigns?** (`id: gates.sub-campaign`)
    - Answer: ask me
12. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: ask me if review is enabled

# Benchmark recording questions

13. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `<repo-checkout>/crustify/results.md`, standard template

# Additional instructions

The deterministic `crustify scan-unsafe <workdir>` checks remain enabled independently
of agentic review.
