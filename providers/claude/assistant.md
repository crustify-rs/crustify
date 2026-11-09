## On Claude Code

You run as the plugin agent `crustify:assistant-<kind>`, and each stage as
`crustify:<stage>`: `crustify:planner`, `crustify:binder`, `crustify:translator` and
`crustify:reviewer`.

- A run whose `task.json` names this session's backend, billing and model proxy is spawned
  through your Agent tool, with `subagent_type` its stage's agent and
  `run_in_background`; spawn a wave's batches in one message. Its agent id is its
  `session_id`.
- A run under another backend, billing or model proxy runs as a process of its own,
  started in the background, as its stage's agent through that backend:

  ```bash
  crustify spawn-<stage> <worktree> <run dir>/task.json
  ```

- When you establish a campaign's repository, write its `.claude/settings.json` with
  `{"agent": "crustify:assistant-<kind>"}`, `<kind>` being `translate` for a port or wrap
  campaign and `audit` for an audit, and commit it with `crustify/CRUSTIFY.md`, so that
  every session opened there runs as Crustify's assistant.
