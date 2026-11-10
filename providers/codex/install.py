#!/usr/bin/env python3
"""Install Crustify into Codex, from this checkout.

    install.py [--sandbox workspace|full] [--threads N] [--model-proxy openrouter]
               [--model M] [--effort E] [--codex-home DIR] [--dry-run]
    install.py --uninstall [--codex-home DIR]

Codex reads the checkout's Claude Code plugin manifest, `.claude-plugin/plugin.json`, so
the skills and the transcript hook come from the plugin, installed through the checkout's
marketplace, `.agents/plugins/marketplace.json`. A Codex plugin ships no agent roles and
no profiles, so this script composes them into the Codex home:

- `agents/crustify-<stage>.toml`, one role per stage, which the assistant spawns with
  `spawn_agent`; and
- `crustify-<kind>.config.toml`, the assistant's profile per campaign kind, selected with
  `codex --profile crustify-translate` or `codex --profile crustify-audit`.

Each prompt is the generic provider's, without its skill index, since Codex lists the
plugin's skills itself, with `{crustify_root}` as this checkout's path. Codex copies a
plugin into its cache when it installs it and reads no environment variable in a role's
instructions, so the composed files name the checkout's absolute path: rerun this script
after the checkout changes.

Subagents inherit the parent session's sandbox and approval policy, which a role cannot
override, so the profiles carry them for the whole campaign:

- `workspace` (the default): `workspace-write`, with network access and the toolchains'
  and Crustify's homes writable; `--add-dir` at launch adds what else a campaign writes,
  such as the directory its wrappers are cloned in;
- `full`: `danger-full-access`, for a container that is itself the sandbox.

Subagents also inherit the session's model provider: `--model-proxy` routes the whole
campaign through a gateway, defining its provider in the profiles with the key it reads
from the environment, and `--model`, which a proxy needs, names the model as the proxy
knows it. The assistant passes another model or effort to a stage through `spawn_agent`;
a run on another backend, billing or proxy is a process of its own.

Standard library only: it runs under whatever Python the host has.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "crustify_generic_compose", ROOT / "providers" / "generic" / "compose.py")
generic = importlib.util.module_from_spec(_spec)  # the neutral composer
_spec.loader.exec_module(generic)

#: The marketplace and plugin names, as `.agents/plugins/marketplace.json` gives them.
MARKETPLACE = PLUGIN = "crustify"

#: Each model proxy's Codex provider: its Responses API and the key it reads.
PROXIES = {
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",
                   "wire_api": "responses", "env_key": "OPENROUTER_API_KEY"},
}

#: Each stage's role: its description is the rule the assistant routes a run by.
STAGES = {
    "planner": "Crustify's planner: runs one planner run of a translation campaign on its "
               "planner branch, deciding modules.json, dependencies.json and the plan "
               "fields of schedule.json, in one commit. Use for every planner run.",
    "binder": "Crustify's binder: runs one `wrap` batch from its task.json in its worktree: "
              "binds its items behind a safe Rust API, tests them, and lands them on its "
              "wave branch. Use for every `wrap` batch.",
    "translator": "Crustify's translator: runs one `port`, `port/layout`, `port/memory` or "
                  "`port/unexport` batch from its task.json in its worktree: ports its "
                  "items to safe Rust, tests them, and lands them on its wave branch. Use "
                  "for every port batch.",
    "reviewer": "Crustify's reviewer: runs one review batch from its task.json in its "
                "worktree: reviews landed commits or a crate's paths for its objectives, "
                "files and reproduces findings, fixes them under `fix`, and lands on its "
                "wave branch. Use for every review batch.",
}

#: What the roles' and profiles' instructions add to the generic prompt on Codex.
CODEX_NOTES = """

---

## Codex

You run on Codex. Your agents' roles are `crustify-planner`, `crustify-binder`,
`crustify-translator` and `crustify-reviewer`: spawn each run with `spawn_agent`, with its
role as the agent type, its task message as the task and its run dir's name as its task
name, without forking your history. Every agent shares your working directory, so a task
message names the worktree its agent works in. An agent's session id is its thread id:
when `spawn_agent` returns a task path rather than a thread id, it is the `id` in the
`session_meta` line of the rollout under `$CODEX_HOME/sessions/` whose `agent_path` is
that task path.

Every agent runs on this session's model provider, with its billing and proxy. Pass the
model and effort a run's `args` name with `spawn_agent`'s model and reasoning overrides; a
run whose backend, billing or proxy differs from this session's cannot be spawned here:
report it at preflight.
"""

STAGE_NOTES = """

---

## Codex

You run on Codex, and share the working directory of the agent that spawned you: run every
command in the worktree your task message names, and edit its files by their paths there.
"""


def _toml_str(text: str) -> str:
    """A TOML basic string: JSON's escapes are TOML's, but for DEL, which TOML escapes."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007F")


def role(stage: str) -> str:
    instructions = generic.prompt(stage, root=str(ROOT), index=False) + STAGE_NOTES
    return (f"# Composed by {Path(__file__).relative_to(ROOT)} from {ROOT}; rerun it after "
            f"the checkout changes.\n"
            f"name = {_toml_str('crustify-' + stage)}\n"
            f"description = {_toml_str(STAGES[stage])}\n"
            f"developer_instructions = {_toml_str(instructions)}\n")


def profile(kind: str, sandbox: str, threads: int, proxy: str | None = None,
            model: str | None = None, effort: str | None = None) -> str:
    instructions = generic.prompt("assistant", kind, str(ROOT), index=False) + CODEX_NOTES
    lines = [f"# Composed by {Path(__file__).relative_to(ROOT)} from {ROOT}; rerun it after "
             f"the checkout changes.",
             f"developer_instructions = {_toml_str(instructions)}"]
    if proxy:
        lines.append(f"model_provider = {_toml_str('crustify-' + proxy)}")
    if model:
        lines.append(f"model = {_toml_str(model)}")
    if effort:
        lines.append(f"model_reasoning_effort = {_toml_str(effort)}")
    if sandbox == "full":
        lines += ['sandbox_mode = "danger-full-access"', 'approval_policy = "never"']
    else:
        home = Path.home()
        crustify_home = Path(os.environ.get("CRUSTIFY_HOME", home / ".crustify"))
        roots = [crustify_home, home / ".cargo", home / ".rustup", home / ".cache"]
        lines += ['sandbox_mode = "workspace-write"', 'approval_policy = "on-request"']
    lines += ["", "[agents]", f"max_concurrent_threads_per_session = {threads}"]
    if sandbox != "full":
        lines += ["", "[sandbox_workspace_write]", "network_access = true",
                  "writable_roots = [" + ", ".join(_toml_str(str(r)) for r in roots) + "]"]
    if proxy:
        # Named apart from any provider of the user's own config, which the profile layers on.
        lines += ["", f"[model_providers.crustify-{proxy}]"]
        lines += [f"{k} = {_toml_str(v)}" for k, v in PROXIES[proxy].items()]
    return "\n".join(lines) + "\n"


def files(codex_home: Path, sandbox: str, threads: int, proxy: str | None = None,
          model: str | None = None, effort: str | None = None) -> dict[Path, str]:
    out = {codex_home / "agents" / f"crustify-{s}.toml": role(s) for s in STAGES}
    for kind in generic.KINDS:
        out[codex_home / f"crustify-{kind}.config.toml"] = profile(
            kind, sandbox, threads, proxy, model, effort)
    return out


def _codex(*args: str, check: bool = True) -> None:
    print("+ codex", " ".join(args))
    subprocess.run(["codex", *args], check=check, stdin=subprocess.DEVNULL)


def probe_sandbox() -> None:
    """Warn when Codex's Linux sandbox cannot start here: every command would fail in it."""
    if not sys.platform.startswith("linux"):
        return
    run = subprocess.run(["codex", "sandbox", "-c", 'sandbox_mode="workspace-write"',
                          "-c", "sandbox_workspace_write.network_access=true", "--", "true"],
                         stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if run.returncode == 0:
        return
    why = [l for l in run.stderr.splitlines() if l.startswith("bwrap")] or [run.stderr.strip()]
    print(f"\nwarning: Codex's sandbox cannot start on this host ({'; '.join(why)}), so every "
          f"command a session runs under the workspace profiles fails. Where the kernel "
          f"restricts unprivileged user namespaces, as Ubuntu's AppArmor does, install the "
          f"distribution's bubblewrap, whose AppArmor profile permits them; or run the "
          f"campaign in a container installed with --sandbox full.", file=sys.stderr)


def install(codex_home: Path, sandbox: str, threads: int, dry_run: bool,
            proxy: str | None = None, model: str | None = None,
            effort: str | None = None) -> None:
    composed = files(codex_home, sandbox, threads, proxy, model, effort)
    if dry_run:
        for path, text in composed.items():
            print(f"would write {path} ({len(text)} bytes)")
        print(f"would add marketplace {MARKETPLACE} from {ROOT} and install {PLUGIN}@{MARKETPLACE}")
        return
    if not shutil.which("codex"):
        sys.exit("codex is not on PATH")
    if proxy and not os.environ.get(PROXIES[proxy]["env_key"]):
        print(f"warning: {PROXIES[proxy]['env_key']} is not set; the profiles read it at launch",
              file=sys.stderr)
    if sandbox == "workspace":
        probe_sandbox()
    for path, text in composed.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path}")
    # Reinstalling refreshes the plugin's cached copy from the checkout.
    _codex("plugin", "remove", f"{PLUGIN}@{MARKETPLACE}", check=False)
    _codex("plugin", "marketplace", "remove", MARKETPLACE, check=False)
    _codex("plugin", "marketplace", "add", str(ROOT))
    _codex("plugin", "add", f"{PLUGIN}@{MARKETPLACE}")
    print("\nTrust the plugin's transcript hook once, with /hooks in an interactive session.\n"
          "Then open the assistant in a campaign's directory:\n"
          "  codex --profile crustify-translate   # port or wrap\n"
          "  codex --profile crustify-audit       # audit")


def uninstall(codex_home: Path) -> None:
    for path in files(codex_home, "workspace", 1):
        if path.exists():
            path.unlink()
            print(f"removed {path}")
    if shutil.which("codex"):
        _codex("plugin", "remove", f"{PLUGIN}@{MARKETPLACE}", check=False)
        _codex("plugin", "marketplace", "remove", MARKETPLACE, check=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sandbox", choices=("workspace", "full"), default="workspace")
    parser.add_argument("--threads", type=int, default=16,
                        help="cap on the agent threads a session keeps open, the assistant's "
                             "included (default 16); the concurrency skill decides within it")
    parser.add_argument("--model-proxy", choices=sorted(PROXIES),
                        help="route the campaign's sessions through this gateway, with its "
                             "API key from the environment; needs --model")
    parser.add_argument("--model", help="the model the sessions run, as the proxy knows it "
                                        "(e.g. openai/gpt-5.6-sol); Codex's default without one")
    parser.add_argument("--effort", choices=("minimal", "low", "medium", "high", "xhigh"),
                        help="the sessions' reasoning effort; Codex's default without one")
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    if args.model_proxy and not args.model:
        parser.error("--model-proxy needs --model, the model as the proxy knows it")
    if args.uninstall:
        uninstall(args.codex_home)
    else:
        install(args.codex_home, args.sandbox, args.threads, args.dry_run,
                args.model_proxy, args.model, args.effort)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
