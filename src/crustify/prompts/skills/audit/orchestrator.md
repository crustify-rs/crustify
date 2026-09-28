<!-- SKILL -->

`unsafe` is a per-wave gate and `ub` is a campaign phase. They are the two
halves of this capability and an orchestrator uses both.

## Workflow - base

The following steps augment your base workflow.

### 5. Accounting

Seed the per-wave scan with that wave's exact scheduled names and request JSON;
the unseeded form takes no names:

```bash
crustify <workdir> audit unsafe --name <wave names...> --json
crustify <workdir> audit unsafe --json
```

Run `crustify <workdir> audit ub` only with explicit user approval, and only
where the campaign task asks for it. Its findings arrive as a branch you
inspect and gate, never as work that merges itself.
