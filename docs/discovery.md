# Discovery (not in the prompt)

This text was the Discovery subsection of `agents/crustify.md`, under Fitness, after
Lexicographic optimization. It is kept here, out of the prompt, until a campaign shows
that the agent needs it spelled out. To restore it, put it back in that place, turn the
intro's options back into two (**discovery** and **self-improvement**, both off unless the
user turns them on), and return the Review question about rerunning the harness for each
population.

## Discovery

This section applies only with discovery on.

Ranked objectives can pull against each other. Examples are a hot path whose safe
version is slower than the C, a representation behind the boundary that the C's behavior
makes hard to keep safe, and a finding with more than one fix. In such a case, do not
settle for the first alternative. Generate a population of candidates for the smallest
unit where the objectives conflict:

- Make the candidates differ in design, not in detail.
- Generate them in parallel.
- Check each candidate against the enabled ones of `ub`, `api` and `interop`, and measure
  each with the same harness.
- Keep generating while new candidates still change which one you would choose, within
  the cost that you briefed.

Record every candidate in `.crustify/fitness/`: its unit, what produced it, its metrics and cost,
and its outcome. The outcome is chosen, lost on an objective (name it), or failed `ub`,
`api` or `interop` (name it). The candidates that lost show what each higher-ranked
objective costs. Report that cost.
