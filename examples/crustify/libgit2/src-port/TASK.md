
# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?**
   - Answer: the existing checkout mounted at `/target`, at its current checked-out revision

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?**
   - Answer: port the C implementation to Rust

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also answer
   orchestrator's choice.**
   - Answer: orchestrator's choice of bottom-up subsystems under `src/`, stopping after at least 10K LoC of C has been ported to native Rust

4. **Which agentic backend and model should do the translation work?**
   - Answer: Codex, `gpt-5.6-sol`

5. **Do you want agentic review after translated work lands? If so, which
   backend and model should perform each review?**
   - Answer: yes, after each wave, using claude backend, openrouter
      provider, `claude-opus-5` model

6. **Should the campaign run the optional agentic UB audit pass? If so, which
   backend and model should run it?**
   - Answer: yes, after each sub-campaign, using claude backend, openrouter
      provider, `claude-opus-5` model

7. **Should I run fully autonomously end to end?**
   - Answer: no

8. **Which billing mode should agentic stages use?**
   - Answer: API for Codex translation; API for Claude review and UB audit

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

9. **Should the campaign use the default batching and parallelism settings, or
   customize them?**
   - Answer: max two structs per agent, min 20 fields, max 25 symbols, max 500 LoC;
   parallelism is orchestrator's choice

10. **What batch caps should review agents use? We recommend 3x the translation
    caps so each reviewer sees more related units.**
    - Answer: same as translators

## Autonomy (if question 7 is answered `no`)

11. **Should I wait for your approval before starting the setup phase?**
    - Answer: no
12. **Should I wait for your approval before starting the translation phase?**
    - Answer: yes, after setup identifies and proposes the bottom-up subsystem plan
13. **Should I wait for your approval between sub-campaigns?**
    - Answer: no
14. **Should I wait for your approval before starting review passes?**
    - Answer: no
15. **Should I wait for your approval before starting UB audit passes?**
    - Answer: no

# Benchmark recording questions

16. **Where and in what format should results be recorded?**
    - Answer: `<repo-checkout>/crustify/results.md`, exact structure

# Campaign notes

- Work in `/target` in place. Do not clone, reset, replace, or discard its
  existing branches or partial `crustify/` translation.
- The campaign is in flight but was interrupted. Assess the current state and
  resume from completed artifacts rather than restarting it.
