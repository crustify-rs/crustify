from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import cli, config


class CommandShapeTests(unittest.TestCase):
    """`crustify <command> <workdir> ...`: the command comes first and its
    options follow it, so every command routes to its own handler."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()
        self.task = self.repo / "TASK.md"
        self.task.write_text("task")
        for name in ("MODEL_OVERRIDE", "BILLING"):
            patcher = mock.patch.object(config, name, getattr(config, name))
            patcher.start()
            self.addCleanup(patcher.stop)

    def _run(self, *argv: str) -> dict:
        seen: dict = {}

        def record(name):
            return lambda args: seen.update(handler=name, args=args)

        with (mock.patch.object(sys, "argv", ["crustify", *argv]),
              mock.patch.object(cli, "_handle_orchestrate", record("orchestrate")),
              mock.patch.object(cli, "_handle_spawn_translator", record("spawn-translator")),
              mock.patch.object(cli, "_handle_audit_stage", record("audit-stage")),
              mock.patch.object(cli, "_handle_cost", record("cost"))):
            cli.main()
        return seen

    def test_translate_starts_the_translation_orchestrator(self) -> None:
        seen = self._run("translate", str(self.repo), str(self.task),
                         "--model", "openrouter/anthropic/claude-opus-5",
                         "--billing", "api", "--campaign", "x")
        self.assertEqual(seen["handler"], "orchestrate")
        self.assertEqual(seen["args"].kind, "translate")
        self.assertEqual(seen["args"].campaign, "x")
        self.assertEqual(config.MODEL_OVERRIDE, "openrouter/anthropic/claude-opus-5")
        self.assertEqual(config.BILLING, "api")

    def test_audit_starts_the_audit_orchestrator(self) -> None:
        seen = self._run("audit", str(self.repo), str(self.task), "--task-only")
        self.assertEqual(seen["handler"], "orchestrate")
        self.assertEqual(seen["args"].kind, "audit")
        self.assertTrue(seen["args"].task_only)

    def test_spawn_translator_runs_one_batch(self) -> None:
        seen = self._run("spawn-translator", str(self.repo), "batch.json",
                         "--base-branch", "wave", "--output", "out",
                         "--model", "openai/gpt-5.6")
        self.assertEqual(seen["handler"], "spawn-translator")
        self.assertEqual(seen["args"].base_branch, "wave")
        self.assertEqual(config.MODEL_OVERRIDE, "openai/gpt-5.6")

    def test_audit_stages_take_any_repository(self) -> None:
        """Neither audit stage needs a crustify/ directory, and the auditor's
        own --model does not become the harness-wide override."""
        plain = self.repo / "plain"
        plain.mkdir()
        seen = self._run("scan-unsafe", str(plain), "--json")
        self.assertEqual((seen["handler"], seen["args"].audit_stage),
                         ("audit-stage", "unsafe"))
        seen = self._run("spawn-auditor", str(plain),
                         "--model", "anthropic/claude-opus-5")
        self.assertEqual(seen["args"].audit_stage, "ub")
        self.assertEqual(seen["args"].model, "anthropic/claude-opus-5")
        self.assertIsNone(config.MODEL_OVERRIDE)

    def test_cost_needs_no_workdir(self) -> None:
        seen = self._run("cost", "a.usage.json", "b.usage.json")
        self.assertEqual(seen["handler"], "cost")
        self.assertEqual(len(seen["args"].usage), 2)

    def test_spawn_translator_needs_a_campaign_tree(self) -> None:
        bare = self.repo / "bare"
        bare.mkdir()
        with self.assertRaises(SystemExit):
            self._run("spawn-translator", str(bare), "batch.json",
                      "--base-branch", "wave", "--output", "out")

    def test_old_spellings_are_rejected(self) -> None:
        for argv in (
                (str(self.repo), "orchestrate-translation", str(self.task)),
                ("--model", "x", "translate", str(self.repo), str(self.task)),
                (str(self.repo), "audit", "unsafe")):
            with self.subTest(argv=argv), mock.patch("sys.stderr"), \
                    self.assertRaises(SystemExit):
                self._run(*argv)
