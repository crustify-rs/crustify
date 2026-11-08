from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify.agents.backends import _atomic_write_text
from crustify.core.agentlog import AgentLog
from crustify.core.models import from_model, route


def resolve(model: str, billing: str = "subscription"):
    """The route of an earlier ``<provider>/<model>`` name."""
    return from_model(model, billing)


class AtomicPromptFileTests(unittest.TestCase):
    def test_write_publishes_complete_text_and_removes_temporary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            prompt = directory / "prompt.md"
            _atomic_write_text(prompt, "complete prompt")
            self.assertEqual(prompt.read_text(), "complete prompt")
            self.assertEqual(list(directory.iterdir()), [prompt])


class ProviderRoutingTests(unittest.TestCase):
    def test_earlier_model_names_map_to_routes(self) -> None:
        r = resolve("openrouter/anthropic/claude-opus-5")
        self.assertEqual((r.backend, r.billing, r.model_proxy, r.args),
                         ("claude", "api", "openrouter",
                          ("--model", "anthropic/claude-opus-5")))
        self.assertEqual(r.provider, "openrouter")
        r = resolve("openrouter/openai/gpt-5.6")
        self.assertEqual((r.backend, r.args), ("codex", ("-m", "openai/gpt-5.6")))
        r = resolve("anthropic/claude-opus-5")
        self.assertEqual((r.backend, r.model_proxy, r.provider),
                         ("claude", None, "anthropic"))

    def test_a_route_is_checked(self) -> None:
        self.assertEqual(route("claude").args, ())
        for bad in (dict(backend="gemini"),
                    dict(backend="claude", billing="free"),
                    dict(backend="claude", billing="api", model_proxy="nowhere"),
                    # A proxy bills by its own key.
                    dict(backend="claude", model_proxy="openrouter"),
                    # Codex's default model is no id a proxy knows.
                    dict(backend="codex", billing="api", model_proxy="openrouter")):
            with self.subTest(**bad), self.assertRaises(ValueError):
                route(**bad)
        route("codex", "api", "openrouter", ["-m", "openai/gpt-6-sol"])

    def test_claude_openrouter_route_uses_gateway_key(self) -> None:
        from crustify.agents.backends.claude_cli import ClaudeCliBackend

        captured: dict = {}

        class Process:
            stdout: tuple = ()
            stderr: tuple = ()

            @staticmethod
            def wait() -> int:
                return 0

        def popen(command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]
            return Process()

        with tempfile.TemporaryDirectory() as tmp:
            provider_home = Path(tmp) / "claude"
            with (mock.patch.dict(
                    "os.environ", {"OPENROUTER_API_KEY": "test-key",
                                   "CLAUDE_CODE_CHILD_SESSION": "1"}, clear=True),
                  mock.patch("shutil.which", return_value="/bin/claude"),
                  mock.patch("subprocess.Popen", side_effect=popen)):
                ClaudeCliBackend().run(
                    name="test",
                    route=resolve("openrouter/anthropic/claude-opus-5"),
                    prompt="task",
                    system_preamble="role",
                    work_dir=tmp,
                    log=AgentLog(None, "test", console=False),
                    provider_home=provider_home,
                )

        command = captured["command"]
        env = captured["env"]
        self.assertEqual(command[command.index("--model") + 1],
                         "anthropic/claude-opus-5")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "test-key")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "")
        self.assertNotIn("--bare", command)
        # An agent is a session of its own, so it keeps its transcript even
        # when crustify runs inside a Claude Code session.
        self.assertNotIn("CLAUDE_CODE_CHILD_SESSION", env)

    def _codex_command(self, r) -> list[str]:
        from crustify.agents.backends.codex_cli import CodexCliBackend

        captured: dict = {}

        class Process:
            stdout: tuple = ()
            stderr: tuple = ()

            @staticmethod
            def wait() -> int:
                return 0

        def popen(command, **kwargs):
            captured["command"] = command
            return Process()

        with tempfile.TemporaryDirectory() as tmp:
            with (mock.patch.dict(
                    "os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
                  mock.patch("shutil.which", return_value="/bin/codex"),
                  mock.patch("subprocess.Popen", side_effect=popen)):
                CodexCliBackend().run(
                    name="test", route=r, prompt="task", system_preamble="role",
                    work_dir=tmp, log=AgentLog(None, "test", console=False),
                    provider_home=Path(tmp) / "codex",
                )
        return captured["command"]

    def test_codex_runs_its_default_model_at_high_effort(self) -> None:
        command = self._codex_command(resolve("openrouter/openai/gpt-5.6-sol"))
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("model_provider=openrouter", command)
        # The model is the user's, after crustify's own options.
        self.assertEqual(command[-3:-1], ["-m", "openai/gpt-5.6-sol"])
        command = self._codex_command(route("codex"))
        self.assertNotIn("-m", command)

    def test_the_users_effort_replaces_the_default(self) -> None:
        command = self._codex_command(
            route("codex", args=["-c", 'model_reasoning_effort="xhigh"']))
        self.assertNotIn('model_reasoning_effort="high"', command)
        self.assertIn('model_reasoning_effort="xhigh"', command)

    def test_translator_resolves_the_same_backend_registry(self) -> None:
        from crustify.agents.translate import TranslateAgent

        calls: list[dict] = []

        class Backend:
            def run(self, **kwargs):
                calls.append(kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "crustify").mkdir()
            logs = repo / "logs"
            logs.mkdir()
            agent = TranslateAgent(
                repo,
                route="symbol",
                items=[{
                    "name": "example",
                    "defined_in": "example.h",
                    "kind": "symbol",
                    "field_users": [],
                }],
                git_base="wave-0",
                log_stem="batch",
            )
            with (mock.patch(
                    "crustify.agents.backends.get_backend",
                    return_value=Backend()) as shared,
                  mock.patch("crustify.config.BACKEND", "claude"),
                  mock.patch("crustify.config.BILLING", "api"),
                  mock.patch("crustify.config.MODEL_PROXY", "openrouter"),
                  mock.patch("crustify.config.PROVIDER_ARGS", ["--effort", "high"])):
                agent.run()

        shared.assert_called_once_with("claude")
        r = calls[0]["route"]
        self.assertEqual((r.provider, r.billing, r.args),
                         ("openrouter", "api", ("--effort", "high")))


if __name__ == "__main__":
    unittest.main()


class InteractiveModeTests(unittest.TestCase):
    """An interactive run hands the terminal to the CLI's own interface: no
    print mode, no captured pipes, and the usage record still follows."""

    def _run(self, backend, model: str, tmp: str,
             resume: str | None = None) -> list[str]:
        captured: dict = {}

        def run(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            return mock.Mock(returncode=0)

        with (mock.patch.dict(
                "os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
              mock.patch("shutil.which", return_value="/bin/cli"),
              mock.patch("subprocess.run", side_effect=run),
              mock.patch("subprocess.Popen",
                         side_effect=AssertionError("headless path taken"))):
            backend.run(
                name="orchestrator",
                route=resolve(model),
                prompt="kickoff",
                system_preamble="role",
                work_dir=tmp,
                log=AgentLog(None, "test", console=False),
                provider_home=Path(tmp) / "home",
                interactive=True,
                resume=resume,
            )
        # Inherited stdio: nothing is piped away from the terminal.
        for stream in ("stdin", "stdout", "stderr"):
            self.assertNotIn(stream, captured["kwargs"])
        return captured["command"]

    def test_claude_runs_its_interface_with_the_prompt_first(self) -> None:
        from crustify.agents.backends.claude_cli import ClaudeCliBackend

        with tempfile.TemporaryDirectory() as tmp:
            command = self._run(ClaudeCliBackend(),
                                "openrouter/anthropic/claude-opus-5", tmp)
        self.assertEqual(command[1], "kickoff")
        # Headless-only flags.
        for flag in ("-p", "--output-format", "--verbose"):
            self.assertNotIn(flag, command)
        self.assertIn("--append-system-prompt-file", command)
        self.assertIn("--session-id", command)

    def test_claude_resumes_the_session_without_forking_it(self) -> None:
        from crustify.agents.backends.claude_cli import ClaudeCliBackend

        with tempfile.TemporaryDirectory() as tmp:
            command = self._run(ClaudeCliBackend(),
                                "openrouter/anthropic/claude-opus-5", tmp,
                                resume="s-1")
        self.assertEqual(command[command.index("--resume") + 1], "s-1")
        self.assertNotIn("--session-id", command)
        self.assertNotIn("--fork-session", command)
        # The system prompt is not kept with the conversation: it goes again.
        self.assertIn("--append-system-prompt-file", command)

    def test_codex_resumes_the_session(self) -> None:
        from crustify.agents.backends.codex_cli import CodexCliBackend

        with tempfile.TemporaryDirectory() as tmp:
            command = self._run(CodexCliBackend(),
                                "openrouter/openai/gpt-5.6", tmp, resume="r-1")
        self.assertEqual(command[1], "resume")
        self.assertEqual(command[-2:], ["r-1", "kickoff"])
        self.assertIn("model_instructions_file", " ".join(command))

    def test_codex_runs_its_interface_without_exec_only_flags(self) -> None:
        from crustify.agents.backends.codex_cli import CodexCliBackend

        with tempfile.TemporaryDirectory() as tmp:
            command = self._run(CodexCliBackend(),
                                "openrouter/openai/gpt-5.6", tmp)
        self.assertNotIn("exec", command)
        for flag in ("--skip-git-repo-check", "--ignore-user-config"):
            self.assertNotIn(flag, command)
        self.assertEqual(command[command.index("-a") + 1], "never")
        self.assertEqual(command[-1], "kickoff")


class SystemPromptFileTests(unittest.TestCase):
    """The preamble travels as a file: a single argv element is capped at
    MAX_ARG_STRLEN (32 pages) however large ARG_MAX is, and the translate
    preamble exceeds it."""

    def test_file_holds_the_text_and_is_removed_after_the_run(self) -> None:
        from crustify.agents.backends import system_prompt_file

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "home"
            with system_prompt_file("preamble", directory=directory) as path:
                self.assertEqual(path.read_text(), "preamble")
                self.assertEqual(path.parent, directory)
            self.assertFalse(path.exists())
            self.assertEqual(list(directory.iterdir()), [])

    def test_file_is_removed_even_when_the_run_raises(self) -> None:
        from crustify.agents.backends import system_prompt_file

        with self.assertRaises(RuntimeError):
            with system_prompt_file("preamble") as path:
                held = path
                raise RuntimeError("the CLI failed")
        self.assertFalse(held.exists())

    def test_concurrent_runs_of_one_preamble_get_their_own_files(self) -> None:
        from crustify.agents.backends import system_prompt_file

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with system_prompt_file("same", directory=directory) as first, \
                 system_prompt_file("same", directory=directory) as second:
                self.assertNotEqual(first, second)
                self.assertEqual(len(list(directory.iterdir())), 2)

    def test_a_preamble_over_the_argv_cap_still_travels(self) -> None:
        from crustify.agents.backends import system_prompt_file

        oversized = "x" * (32 * 4096 + 1)
        with system_prompt_file(oversized) as path:
            self.assertEqual(len(path.read_bytes()), len(oversized))


class ClaudeHeadlessTests(unittest.TestCase):
    """What a headless claude run is given: bypassed permissions, the user's
    forwarded options last, and under API billing a config dir of its own."""

    def _run(self, tmp: str, env: dict, **kwargs) -> tuple[list[str], dict]:
        from crustify.agents.backends.claude_cli import ClaudeCliBackend

        captured: dict = {}

        class Process:
            stdout: tuple = ()
            stderr: tuple = ()

            @staticmethod
            def wait() -> int:
                return 0

        def popen(command, **kw):
            captured["command"] = command
            captured["env"] = kw["env"]
            return Process()

        r = route("claude", kwargs.pop("billing", "subscription"),
                  None, kwargs.pop("extra_args", ()))

        with (mock.patch.dict("os.environ", env, clear=True),
              mock.patch("shutil.which", return_value="/bin/claude"),
              mock.patch("subprocess.Popen", side_effect=popen)):
            with AgentLog(Path(tmp) / "logs", "test", console=False) as log:
                ClaudeCliBackend().run(
                    name="test",
                    route=r,
                    prompt="task",
                    system_preamble="role",
                    work_dir=tmp,
                    log=log,
                    **kwargs,
                )
            captured["record"] = json.loads(
                (Path(tmp) / "logs" / "test.session.json").read_text())
        self.record = captured["record"]
        return captured["command"], captured["env"]

    def test_headless_run_bypasses_permissions_and_restricts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            command, env = self._run(tmp, {"HOME": tmp})
        self.assertEqual(
            command[command.index("--permission-mode") + 1], "bypassPermissions")
        for flag in ("--tools", "--setting-sources", "--strict-mcp-config",
                     "--disable-slash-commands", "--add-dir", "--bare"):
            self.assertNotIn(flag, command)
        self.assertNotIn("CLAUDE_CONFIG_DIR", env)
        # The CLI's default model: crustify names none.
        self.assertNotIn("--model", command)
        # The record is what reruns or prices the session, not where its
        # transcript was.
        self.assertEqual(
            {k: self.record[k] for k in
             ("backend", "billing", "model_proxy", "args", "exit_code")},
            {"backend": "claude", "billing": "subscription",
             "model_proxy": None, "args": [], "exit_code": 0})
        for gone in ("transcript", "model", "provider", "cli"):
            self.assertNotIn(gone, self.record)

    def test_forwarded_options_come_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            command, _ = self._run(tmp, {"HOME": tmp},
                                   extra_args=["--effort", "high"])
        self.assertEqual(command[-2:], ["--effort", "high"])

    def test_api_billing_uses_a_config_dir_without_a_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            own = Path(tmp) / "own"
            own.mkdir()
            (own / "settings.json").write_text("{}")
            (own / ".credentials.json").write_text("{}")
            home = Path(tmp) / "providers" / "claude"
            command, env = self._run(
                tmp, {"HOME": tmp, "CLAUDE_CONFIG_DIR": str(own),
                      "ANTHROPIC_API_KEY": "test-key"},
                billing="api", provider_home=home)
            self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(home.resolve()))
            self.assertNotIn("--bare", command)
            # The user's settings follow the agent; their login does not.
            self.assertTrue((home / "settings.json").is_symlink())
            self.assertFalse((home / ".credentials.json").exists())


class ProviderArgsTests(unittest.TestCase):
    """`--` ends crustify's options: the rest go to the provider CLI."""

    def test_codex_takes_them_before_the_first_turn(self) -> None:
        from crustify.agents.backends.codex_cli import CodexCliBackend

        captured: dict = {}

        def run(command, **kwargs):
            captured["command"] = command
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict("os.environ", {"HOME": tmp,
                                               "CODEX_HOME": tmp}, clear=True), \
                mock.patch("shutil.which", return_value="/bin/codex"), \
                mock.patch("subprocess.run", side_effect=run):
            CodexCliBackend().run(
                name="test",
                route=route("codex", args=["-c", "x=1"]),
                prompt="kickoff",
                system_preamble="role",
                work_dir=tmp,
                log=AgentLog(None, "test", console=False),
                interactive=True,
            )
        command = captured["command"]
        self.assertEqual(command[-3:], ["-c", "x=1", "kickoff"])

    def test_the_command_line_splits_at_the_anchor(self) -> None:
        from crustify import cli, config

        seen: dict = {}
        with mock.patch("sys.argv", ["crustify", "usage", "s-1", "t.jsonl",
                                     "--", "--effort", "high"]), \
                mock.patch.object(cli, "_handle_usage",
                                  side_effect=lambda a: seen.update(a=a)), \
                mock.patch.object(config, "PROVIDER_ARGS", []):
            try:
                cli.main()
            except SystemExit:
                pass
            forwarded = list(config.PROVIDER_ARGS)
        self.assertEqual(forwarded, ["--effort", "high"])
