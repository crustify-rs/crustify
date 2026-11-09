## On Claude Code

You run as the plugin agent `crustify:assistant-<kind>`, and each stage as
`crustify:<stage>`: `crustify:planner`, `crustify:binder`, `crustify:translator` and
`crustify:reviewer`. Crustify's checkout is `${CLAUDE_PLUGIN_ROOT}`.

### Spawning a stage

A run whose `task.json` names this session's backend, billing and model proxy is spawned
through your Agent tool, with `subagent_type` its stage's agent, `run_in_background`, and
its task message as its `prompt`; spawn a wave's batches in one message. Its agent id is
its `session_id`, and its transcript is copied into Crustify's home as it ends.

A run under another billing or model proxy runs as a `claude` process of its own, started
in the background from its worktree, with a session id you choose and record first:

```bash
sid=$(python3 -c 'import uuid; print(uuid.uuid4())')   # its task's session_id
cd <worktree> && env -u CLAUDE_CODE_CHILD_SESSION <billing environment> \
  claude -p --plugin-dir "${CLAUDE_PLUGIN_ROOT}" --agent crustify:<stage> \
    --session-id "$sid" --permission-mode bypassPermissions <the task's args> \
    "<task message>" < /dev/null > <run dir>/agent.log 2>&1
```

- `CLAUDE_CODE_CHILD_SESSION` is unset, because a session started from inside this one
  otherwise saves no transcript, and the run would have nothing to be priced by.
- Under a model proxy, the billing environment points Claude Code at the proxy's
  Anthropic-compatible endpoint, and blanks the direct key, which it would otherwise
  prefer: for `openrouter`, `ANTHROPIC_BASE_URL=https://openrouter.ai/api`,
  `ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY` and `ANTHROPIC_API_KEY=`.
- Under `api` billing without a proxy, `ANTHROPIC_API_KEY` alone does not switch Claude
  Code away from a stored subscription login, so the run also gets a config home of its
  own that holds none, `CLAUDE_CONFIG_DIR=~/.crustify/providers/claude`, with your own
  `settings.json`, `CLAUDE.md`, `skills`, `commands` and `agents` linked into it.
- Its transcript is `<config home>/projects/<worktree path, with every non-alphanumeric
  character as ->/<session id>.jsonl`; copy it into Crustify's home when the run ends.

Check that the variables its billing and model proxy need are set, without printing their
values, and that `claude --version` answers, before you spawn the first run of a backend.

### The repository

When you establish a campaign's repository, write its `.claude/settings.json` with
`{"agent": "crustify:assistant-<kind>"}`, `<kind>` being `translate` for a port or wrap
campaign and `audit` for an audit, and commit it with `crustify/CRUSTIFY.md`, so that
every session opened there runs as Crustify's assistant.

### Pricing

`crustify-usage` is `${CLAUDE_PLUGIN_ROOT}/utils/crustify-usage`.
