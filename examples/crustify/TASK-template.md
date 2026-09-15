
Fill in as many answers as you want before starting the orchestrator. It will
ask only for campaign decisions that remain unresolved.

# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?** (`id: source`)
   - Answer: `<repository URL>, <commit or tag>`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?** (`id: objective`)
   - Answer: `<port | wrap>`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.** (`id: scope`)
   - Answer: `<named subsystems | named functions/types | whole target |
     orchestrator's choice>`

4. **Which model and billing should do the translation work?**
   (`id: translate-agent`)
   - Answer: `<provider/model, api | subscription>`, e.g.
     `openrouter/anthropic/claude-opus-5, api`. The provider is the first
     segment and selects both the billing rate table and the backend CLI.
     Supported providers:
     - `anthropic/<model>` — Anthropic direct, driven by Claude Code;
     - `openai/<model>` — OpenAI direct, driven by Codex;
     - `openrouter/<vendor>/<model>` — OpenRouter, which resells every vendor
       behind one key, so the vendor segment picks the CLI: `anthropic/*` is
       driven by Claude Code and everything else by Codex. OpenRouter
       supports `api` billing only.

5. **Do you want agentic review after translated work lands? If so, which
   model and billing should perform each review?** (`id: review-agent`)
   - Answer: `<no | provider/model, api | subscription>`

6. **Should the campaign run the optional agentic UB audit pass? If so, which
   model and billing should run it?** (`id: ub-audit`)
   - Answer: `<no | provider/model, api | subscription>`

7. **Should I run fully autonomously end to end?** (`id: autonomy`)
   - Answer: `<yes | no>`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

8. **Should the campaign use the default batching and parallelism settings, or
   customize them?** (`id: workload`)
   - Answer: `<defaults | max-types: N, max-syms: N, max-loc: N,
     parallelism: N | orchestrator's choice>`

9. **What batch caps should review agents use? We recommend the same caps as
   translation by default.** (`id: review-workload`)
   - Answer: `<same as translation | max-types: N,
     max-syms: N, max-loc: N>`

## Autonomy (if question 7 is answered `no`)

Answer these approval-gate questions only if question 7 is answered `no`.

10. **Should I wait for your approval before starting the setup phase?** (`id: gates.setup`)
    - Answer: `<yes | no>`
11. **Should I wait for your approval before starting the translation phase?**
    (`id: gates.translation`)
    - Answer: `<yes | no>`
12. **Should I wait for your approval between sub-campaigns?** (`id: gates.sub-campaign`)
    - Answer: `<yes | no | not applicable>`
13. **Should I wait for your approval before starting review passes?** (`id: gates.review`)
    - Answer: `<yes | no | not applicable>`
14. **Should I wait for your approval before starting UB audit passes?**
    (`id: gates.ub-audit`)
    - Answer: `<yes | no | not applicable>`

# Benchmark recording questions

15. **Where and in what format should results be recorded?** (`id: results`)
    - Answer: `<results path>, <standard | custom template>`

# Additional instructions

Unless otherwise stated, preserve the format of the results doc exactly.

