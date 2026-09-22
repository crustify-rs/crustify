<!-- SKILL -->

- Treat the wave worklist as fixed. Use oracle queries to understand an
  item and submit ownership findings, never to expand the scheduled batch.
- Read `query {types|symbols|dag} --help` before the first query and submit
  findings only through `--update`.
- The submitted sub-campaign schedule is orchestrator state. Do not edit or regenerate it from an
  agent worktree.


  ## Moved from playbook


Use the enabled analysis capability when present. Submit missing agent-owned
findings through its update interface and resolve rejected or inconsistent
records. Never edit derived analysis files. Without that capability, derive
the same facts from source.

Use the campaign-wide Wavefront configuration supplied in the task for
queries. Do not substitute a narrow scheduling configuration from a wave
directory. The schedule should contain each dependency or place it in an
earlier wave, except explicit SCC cuts.
