"""Drive one crustify stage with the ``claude`` CLI.

One subprocess per agent, invoked with ``--output-format stream-json`` so
each turn reaches ``<stage>.log`` **as it happens**. The CLI's default text
mode buffers: it prints the final result and nothing else, so a run that
takes twenty minutes shows a 0-byte log for twenty minutes and then
everything at once. That is indistinguishable from a hung agent, and it was
- watching manifest mtimes was the only way to tell a working run from a
stalled one. Streaming costs crustify a renderer (:func:`_render`), which
is the trade the module previously declined; observability during the run
turned out to be worth more than not owning one.

Accounting still comes from the session transcript the CLI persists
independently of stdout format, priced by ``crustify usage``.

Why not ``--output-format json``, which reports ``total_cost_usd``
directly: it is the same buffering problem (one JSON blob at exit), and
under subscription auth ``total_cost_usd`` is the API-equivalent price
rather than what is billed - so pricing every provider by one method makes
the numbers comparable across providers, which mixing provider-reported and
self-computed dollars would not.

The transcript's one blind spot: auxiliary requests the CLI makes on the
side (session-title generation) bill to the account but are never written
as ``assistant`` entries, so summing undercounts by their fixed cost -
measured at 540 input / 14 output tokens, i.e. $0.0006 on a Haiku run.
That is a per-session constant, negligible against an agent that burns
six figures of tokens, and it is a floor rather than a drift.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from crustify.agents.backends import system_prompt_file
from crustify.core.agentlog import AgentLog
from crustify.core.models import PROXIES, Route

# Tool-result payloads can be a whole file; keep the log readable.
_RESULT_CLIP = 2000


def _render(evt: dict) -> list[str]:
    """One ``stream-json`` event -> the lines to log, mirroring the shape the
    codex backend's text mode produces (a tool call, then its output).

    Unknown event types render as nothing rather than raw JSON: the stream
    carries bookkeeping (init handshakes, partial deltas) that is noise in a
    log meant to be read. Anything genuinely unparseable is passed through by
    the caller instead.
    """
    out: list[str] = []
    kind = evt.get("type")

    if kind == "system" and evt.get("subtype") == "init":
        out.append(f"model: {evt.get('model')}  session: {evt.get('session_id')}"
                   f"  cwd: {evt.get('cwd')}")
        return out

    if kind == "assistant":
        for b in (evt.get("message") or {}).get("content") or []:
            if b.get("type") == "text" and b.get("text", "").strip():
                out.append(b["text"].rstrip())
            elif b.get("type") == "thinking" and b.get("thinking", "").strip():
                out.append("[thinking] " + b["thinking"].strip()[:400])
            elif b.get("type") == "tool_use":
                inp = b.get("input") or {}
                # A shell command is shown as itself rather than a JSON blob.
                cmd = inp.get("command")
                out.append(f"exec {cmd}" if cmd
                           else f"tool {b.get('name')} {json.dumps(inp)[:300]}")
        return out

    if kind == "user":
        for b in (evt.get("message") or {}).get("content") or []:
            if b.get("type") != "tool_result":
                continue
            c = b.get("content")
            if isinstance(c, list):
                c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
            c = (c or "").rstrip()
            if not c:
                continue
            flag = " (error)" if b.get("is_error") else ""
            clipped = c[:_RESULT_CLIP]
            out.append(f"  ->{flag} {clipped}"
                       + ("… [clipped]" if len(c) > _RESULT_CLIP else ""))
        return out

    if kind == "result":
        # On success `result` merely repeats the final assistant message, which
        # has already been logged — print it only when the run ended some other
        # way, where it carries the reason and nothing else has.
        if evt.get("subtype") != "success":
            out.append(f"[result: {evt.get('subtype')}]")
            if (txt := (evt.get("result") or "").strip()):
                out.append(txt)
        out.append(f"[turns: {evt.get('num_turns')}  "
                   f"duration: {evt.get('duration_ms')}ms]")
    return out

from crustify.core.usage import claude_config_dir

#: What a config dir of crustify's takes from the operator's own: their
#: settings, instructions, skills, commands and agents. Never the login, nor
#: `.claude.json`, which is the CLI's own state.
_SHARED_CONFIG = ("settings.json", "CLAUDE.md", "skills", "commands", "agents")


def _share_user_config(config_dir: Path) -> None:
    """Create ``config_dir`` if needed, and link the operator's own
    configuration into it, so that an API-billed agent runs under the same
    settings as a subscription one."""
    config_dir.mkdir(parents=True, exist_ok=True)
    own = claude_config_dir()
    if own.resolve() == config_dir:
        return
    for name in _SHARED_CONFIG:
        src, dst = own / name, config_dir / name
        if src.exists() and not dst.exists() and not dst.is_symlink():
            dst.symlink_to(src)


class ClaudeCliBackend:
    def run(
        self,
        *,
        name: str,
        route: Route,
        prompt: str,
        system_preamble: str,
        work_dir: str,
        log: AgentLog,
        override_base_prompt: bool = False,
        provider_home: Path | None = None,
        interactive: bool = False,
        resume: str | None = None,
        session_id: str | None = None,
        on_session: Callable[[str], None] | None = None,
    ) -> None:
        exe = shutil.which("claude")
        if exe is None:
            raise SystemExit(
                "claude backend: the `claude` CLI is not on PATH."
            )

        wd = Path(work_dir).resolve()
        # A resumed session keeps its id, and its transcript grows: it is not
        # forked, which would copy the earlier turns into a new transcript and
        # count their cost twice.
        session_id = resume or session_id or str(uuid.uuid4())
        if on_session is not None:
            on_session(session_id)

        # An interactive session may open with no first turn: the user types
        # it. The prompt goes first, so that no variadic option the user
        # forwards reads it as one of its values.
        cmd = ([exe, prompt] if prompt else [exe]) if interactive else [
            exe, "-p", prompt,
            # Stream each turn as it happens; `--verbose` is what the CLI
            # requires to emit the per-turn events in print mode rather than
            # only the final result.
            "--output-format", "stream-json",
            "--verbose",
        ]
        # No model: the CLI runs its own default unless the user's arguments
        # name one.
        cmd += [*(("--resume", session_id) if resume
                  else ("--session-id", session_id))]
        # The CLI's default tools, settings, MCP servers and skills all apply.
        # Nobody answers a permission prompt in a headless run, where one
        # would deny the tool call, so permissions are bypassed there; an
        # interactive session asks the person at the terminal.
        if not interactive:
            cmd += ["--permission-mode", "bypassPermissions"]
        # Role-owned system text is unconditional. The option decides only
        # whether Claude's own base prompt survives underneath it. It travels
        # as a file, not as an argument: see system_prompt_file.
        preamble_flag = ("--system-prompt-file" if override_base_prompt
                         else "--append-system-prompt-file")
        env = dict(os.environ)
        # Claude Code marks the processes it starts as child sessions, and a
        # child session saves no transcript. Crustify run from a Claude Code
        # session would pass that marker on, and its agents would leave no
        # transcript to price them by. Each agent is a session of its own,
        # whatever started crustify.
        env.pop("CLAUDE_CODE_CHILD_SESSION", None)
        if route.model_proxy is not None:
            proxy = PROXIES[route.model_proxy]
            key = env.get(proxy.key_env)
            if not key:
                raise SystemExit(
                    f"claude backend: model proxy {route.model_proxy} needs "
                    f"{proxy.key_env} in the environment; without it the CLI "
                    "issues no request and exits 0 having done nothing."
                )
            # Claude Code reaches Anthropic-compatible gateways through this
            # endpoint and bearer-token pair. The direct Anthropic key is
            # blanked, because the CLI otherwise prefers it over the token.
            env["ANTHROPIC_BASE_URL"] = proxy.anthropic_url
            env["ANTHROPIC_AUTH_TOKEN"] = key
            env["ANTHROPIC_API_KEY"] = ""
        elif route.billing == "api":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise SystemExit(
                    "claude backend: --billing api needs ANTHROPIC_API_KEY "
                    "in the environment; without it the CLI issues no request "
                    "and exits 0 having done nothing."
                )
            # Exporting ANTHROPIC_API_KEY alone does not switch the CLI to
            # it: it keeps sending the stored subscription login (verified on
            # the wire). A config dir of crustify's holds no login, so the key
            # is the only credential, without `--bare` and all it turns off.
            if provider_home is None:
                raise SystemExit(
                    "claude backend: API billing requires a provider home.")
            config_dir = provider_home.resolve()
            _share_user_config(config_dir)
            env["CLAUDE_CONFIG_DIR"] = str(config_dir)

        with system_prompt_file(system_preamble) as preamble:
            cmd += [preamble_flag, str(preamble)]
            # The user's arguments go last, so they override crustify's.
            cmd += list(route.args)
            if interactive:
                # The terminal is the CLI's: nothing is captured, so the
                # session transcript is the record of what was said.
                log.line(f"[crustify] {name}: interactive session {session_id}")
                rc = subprocess.run(cmd, cwd=str(wd), env=env).returncode
            else:
                rc = self._stream(cmd, wd, env, log)

        log.session({**route.record(), "session_id": session_id,
                     "exit_code": rc, "resumed": bool(resume)})

        if rc != 0:
            raise SystemExit(
                f"claude backend: `claude` exited {rc} for {name}. "
                f"See the agent log for its output."
            )

    @staticmethod
    def _stream(cmd: list[str], wd: Path, env: dict, log: AgentLog) -> int:
        """Run headless and render the stream-json events into ``log``."""
        proc = subprocess.Popen(
            cmd, cwd=str(wd), env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        # Drain stderr on its own thread: reading the two pipes in sequence
        # deadlocks as soon as either fills its buffer.
        err_thread = threading.Thread(
            target=lambda: [log.stderr(ln) for ln in proc.stderr],
            daemon=True,
        )
        err_thread.start()
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
            except ValueError:
                log.line(line)          # not an event — pass through verbatim
                continue
            for out in _render(evt):
                log.line(out)
        rc = proc.wait()
        err_thread.join(timeout=5)
        return rc
