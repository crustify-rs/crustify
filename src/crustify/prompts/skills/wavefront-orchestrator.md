<!-- SKILL -->

Additional role guidance for a Crustify orchestrator:

- Read wavefront's CLI helpstring via `--help` to learn how to use it.

## For Phase 1: Setup

- Wavefront requires the CodeQL T1/T2 tables for computing dependencies; do this
  after building the baseline.

- After builds complete, configure a campaign-wide `wavefront-config.json`
  that every translator agent will resolve its queries through.
