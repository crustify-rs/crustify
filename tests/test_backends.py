from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify.agents.backends import _atomic_write_text
from crustify.core.agentlog import AgentLog
from crustify.core.models import resolve


class AtomicPromptFileTests(unittest.TestCase):
    def test_write_publishes_complete_text_and_removes_temporary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            prompt = directory / "prompt.md"
            _atomic_write_text(prompt, "complete prompt")
            self.assertEqual(prompt.read_text(), "complete prompt")
            self.assertEqual(list(directory.iterdir()), [prompt])


class ProviderRoutingTests(unittest.TestCase):
    def test_openrouter_anthropic_models_use_claude_backend(self) -> None:
        route = resolve("openrouter/anthropic/claude-opus-5")
        self.assertEqual(route.backend, "claude_cli")
        self.assertEqual(route.provider, "openrouter")
        self.assertEqual(route.model, "anthropic/claude-opus-5")
        self.assertEqual(
            resolve("openrouter/openai/gpt-5.6").backend,
            "codex_cli",
        )

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
                  mock.patch("subprocess.Popen", side_effect=popen),
                  mock.patch(
                      "crustify.agents.backends.claude_cli._transcript_path",
                      return_value=None)):
                ClaudeCliBackend().run(
                    name="test",
                    route=resolve("openrouter/anthropic/claude-opus-5"),
                    prompt="task",
                    system_preamble="role",
                    work_dir=tmp,
                    log=AgentLog(None, "test", console=False),
                    billing="api",
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

    def test_openrouter_openai_model_gets_high_reasoning_effort(self) -> None:
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
            provider_home = Path(tmp) / "codex"
            with (mock.patch.dict(
                    "os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
                  mock.patch("shutil.which", return_value="/bin/codex"),
                  mock.patch("subprocess.Popen", side_effect=popen)):
                CodexCliBackend().run(
                    name="test",
                    route=resolve("openrouter/openai/gpt-5.6-sol"),
                    prompt="task",
                    system_preamble="role",
                    work_dir=tmp,
                    log=AgentLog(None, "test", console=False),
                    billing="api",
                    provider_home=provider_home,
                )

        self.assertIn('model_reasoning_effort="high"', captured["command"])

    def test_openrouter_gpt_6_models_get_high_reasoning_effort(self) -> None:
        from crustify.agents.backends.codex_cli import _REASONING_EFFORT

        for model in ("gpt-6-sol", "gpt-6-astra", "gpt-6-luna",
                      "gpt-6.1-sol"):
            route = resolve(f"openrouter/openai/{model}")
            self.assertEqual(_REASONING_EFFORT.get(route.model), "high", model)
            self.assertEqual(_REASONING_EFFORT.get(model), "high", model)

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
                    "field_anchors": [],
                }],
                git_base="wave-0",
                artifact_dir=logs,
                log_stem="batch",
            )
            with (mock.patch(
                    "crustify.agents.backends.get_backend",
                    return_value=Backend()) as shared,
                  mock.patch(
                      "crustify.config.MODEL_OVERRIDE",
                      "openrouter/anthropic/claude-opus-5"),
                  mock.patch("crustify.config.BILLING", "api")):
                agent.run()

        shared.assert_called_once_with("claude_cli")
        self.assertEqual(calls[0]["route"].provider, "openrouter")
        self.assertEqual(calls[0]["billing"], "api")


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
                         side_effect=AssertionError("headless path taken")),
              mock.patch(
                  "crustify.agents.backends.claude_cli._transcript_path",
                  return_value=None)):
            backend.run(
                name="orchestrator",
                route=resolve(model),
                prompt="kickoff",
                system_preamble="role",
                work_dir=tmp,
                log=AgentLog(None, "test", console=False),
                billing="api",
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
        # Headless-only flags; slash commands such as /model stay available.
        for flag in ("-p", "--output-format", "--verbose",
                     "--disable-slash-commands"):
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
