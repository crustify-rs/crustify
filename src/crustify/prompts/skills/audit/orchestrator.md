<!-- SKILL -->

For a Crustify campaign, `unsafe` is a per-wave gate and `ub` is a campaign
phase. Run `crustify <workdir> audit unsafe --name <wave names...> --json` on
every landed wave before promoting it, seeded with the exact scheduled C
names, and record an unseeded scan at campaign end.

Run `crustify <workdir> audit ub` only with explicit user approval, and only
where the campaign task asks for it. Its findings arrive as a branch you
inspect and gate, never as work that merges itself.
