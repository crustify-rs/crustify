from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify.agents.backends.codex_cli import _atomic_write_text
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
                    "os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
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

    def test_auditor_resolves_the_shared_backend_registry(self) -> None:
        from crustify_audit.agents.base import AuditAgent
        from crustify_audit.layout import Layout

        calls: list[dict] = []

        class Backend:
            def run(self, **kwargs):
                calls.append(kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            layout = Layout(Path(tmp))
            with mock.patch(
                    "crustify.agents.backends.get_backend",
                    return_value=Backend()) as shared:
                AuditAgent(
                    layout,
                    model="openrouter/anthropic/claude-opus-5",
                    timeout_s=None,
                    billing="api",
                ).run()

        shared.assert_called_once_with("claude_cli")
        self.assertEqual(calls[0]["route"].provider, "openrouter")
        self.assertEqual(calls[0]["billing"], "api")

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
                objective="wrap",
                campaign_objective="wrap",
                workdir=repo,
                git_base="wave-0",
                log_dir=logs,
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
