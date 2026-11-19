#!/usr/bin/env python3
"""Install Crustify into Codex, from this checkout.

    install.py [--sandbox workspace|full] [--threads N] [--model-proxy openrouter]
               [--model M] [--effort E] [--codex-home DIR] [--dry-run]
    install.py --uninstall [--codex-home DIR]

Codex reads the checkout's Claude Code plugin manifest, `.claude-plugin/plugin.json`, so
the skills come from the plugin, installed through the checkout's marketplace,
`.agents/plugins/marketplace.json`. A Codex plugin ships no profiles, so this script
composes Crustify's into the Codex home, `crustify.config.toml`, selected with
`codex --profile crustify`. Its prompt is the generic provider's, without its skill index,
since Codex lists the plugin's skills itself, with `{crustify_root}` as this checkout's
path. Codex copies a plugin into its cache when it installs it and reads no environment
variable in a profile's instructions, so the composed file names the checkout's absolute
path: rerun this script after the checkout changes.

Subagents inherit the parent session's sandbox and approval policy, so the profile carries
them for the whole port:

- `workspace` (the default): `workspace-write`, with network access and the toolchains'
  and Crustify's homes writable; `--add-dir` at launch adds what else the port writes;
- `full`: `danger-full-access`, for a container that is itself the sandbox.

Subagents also inherit the session's model provider: `--model-proxy` routes the whole
port through a gateway, defining its provider in the profile with the key it reads
from the environment, and `--model`, which a proxy needs, names the model as the proxy
knows it.

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

#: What the profile's instructions add to the generic prompt on Codex.
CODEX_NOTES = """

---

## Codex

You run on Codex. Spawn your subagents with `spawn_agent`, without forking your history.
Every agent shares your working directory, so a subagent's brief names the directory it
works in.
"""


def _toml_str(text: str) -> str:
    """A TOML basic string: JSON's escapes are TOML's, but for DEL, which TOML escapes."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007F")


def profile(sandbox: str, threads: int, proxy: str | None = None,
            model: str | None = None, effort: str | None = None) -> str:
    instructions = generic.prompt(str(ROOT), index=False) + CODEX_NOTES
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
    return {codex_home / "crustify.config.toml":
            profile(sandbox, threads, proxy, model, effort)}


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
          f"port in a container installed with --sandbox full.", file=sys.stderr)


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
    print("\nOpen Crustify in the codebase's directory:\n  codex --profile crustify")


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
                        help="cap on the agent threads a session keeps open, the main "
                             "agent's included (default 16)")
    parser.add_argument("--model-proxy", choices=sorted(PROXIES),
                        help="route the port's sessions through this gateway, with its "
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
