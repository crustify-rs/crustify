
Fill in as many answers as you want before starting the orchestrator. It will
ask only for campaign decisions that remain unresolved.

# Mandatory questions

## Campaign

1. **Which repository and revision should this campaign use?**
   - Answer: `<repository URL>, <commit or tag>`

2. **Should this campaign port the C implementation to Rust, or create safe
   Rust wrappers?**
   - Answer: `<port | wrap>`

3. **What should this campaign target: a named subset of subsystems, or a named
   subset of functions and types, or the whole target repo? You can define them
   now or we can brainstorm them during the live session. You can also let the
   orchestrator decide.**
   - Answer: `<named subsystems | named functions/types | whole target |
     orchestrator's choice>`

4. **Which agentic backend, model, and billing should do the translation work?**
   - Answer: `<backend, model, API | subscription billing>`

5. **Do you want agentic review after translated work lands? If so, which
   backend, model, and API should perform each review?**
   - Answer: `<no | backend, model, API | subscription billing ...>`

6. **Should the campaign run the optional agentic UB audit pass? If so, which
   backend, model, and billing should run it?**
   - Answer: `<no | backend, model, API | subscription billing>`

7. **Should I run fully autonomously end to end?**
   - Answer: `<yes | no>`

# Optional questions

Unanswered optional questions use their defaults.

## Campaign execution

8. **Should the campaign use the default batching and parallelism settings, or
   customize them?**
   - Answer: `<defaults | max-types: N, max-syms: N, max-loc: N,
     parallelism: N | orchestrator's choice>`

9. **What batch caps should review agents use? We recommend the same caps as
   translation by default.**
   - Answer: `<same as translation | max-types: N,
     max-syms: N, max-loc: N>`

## Autonomy (if question 7 is answered `no`)

Answer these approval-gate questions only if question 7 is answered `no`.

10. **Should I wait for your approval before starting the setup phase?**
    - Answer: `<yes | no>`
11. **Should I wait for your approval before starting the translation phase?**
    - Answer: `<yes | no>`
12. **Should I wait for your approval between sub-campaigns?**
    - Answer: `<yes | no | not applicable>`
13. **Should I wait for your approval before starting review passes?**
    - Answer: `<yes | no | not applicable>`
14. **Should I wait for your approval before starting UB audit passes?**
    - Answer: `<yes | no | not applicable>`

# Benchmark recording questions

15. **Where and in what format should results be recorded?**
    - Answer: `<results path>, <standard | custom template>`

# Additional instructions

Unless otherwise stated, preserve the format of the results doc exactly.

