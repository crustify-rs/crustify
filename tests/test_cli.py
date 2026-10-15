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
              mock.patch.object(cli, "_handle_spawn_worklist", record("spawn-worklist")),
              mock.patch.object(cli, "_handle_spawn_reviewer", record("spawn-reviewer")),
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
        self.assertEqual(seen["handler"], "spawn-worklist")
        self.assertEqual(seen["args"].role, "translator")
        self.assertEqual(seen["args"].base_branch, "wave")
        self.assertEqual(config.MODEL_OVERRIDE, "openai/gpt-5.6")

    def test_spawn_binder_runs_one_batch(self) -> None:
        seen = self._run("spawn-binder", str(self.repo), "batch.json",
                         "--base-branch", "wave", "--output", "out")
        self.assertEqual(seen["handler"], "spawn-worklist")
        self.assertEqual(seen["args"].role, "binder")

    def test_spawn_reviewer_runs_one_review_batch(self) -> None:
        seen = self._run("spawn-reviewer", str(self.repo), "batch.json",
                         "--base-branch", "review-wave", "--output", "out",
                         "--dry-run")
        self.assertEqual(seen["handler"], "spawn-reviewer")
        self.assertEqual(seen["args"].base_branch, "review-wave")
        self.assertTrue(seen["args"].dry_run)

    def test_spawn_reviewer_needs_a_campaign_tree(self) -> None:
        bare = self.repo / "bare"
        bare.mkdir()
        with self.assertRaises(SystemExit):
            self._run("spawn-reviewer", str(bare), "batch.json",
                      "--base-branch", "wave", "--output", "out")

    def test_spawn_auditor_is_gone(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._run("spawn-auditor", str(self.repo))

    def test_an_audit_can_be_resumed(self) -> None:
        seen = self._run("audit", str(self.repo), str(self.task),
                         "--campaign", "a1")
        self.assertEqual(seen["args"].campaign, "a1")

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


class CanonicalTaskTests(unittest.TestCase):
    """The orchestrator reads its task from `<workdir>/crustify/TASK.md`."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.given = self.repo / "given.md"
        self.given.write_text("answers")
        self.canonical = self.repo / "crustify/TASK.md"

    def test_the_first_run_installs_the_task(self) -> None:
        self.assertEqual(cli.canonical_task(self.repo, self.given),
                         self.canonical)
        self.assertEqual(self.canonical.read_text(), "answers")

    def test_a_resume_needs_no_task(self) -> None:
        cli.canonical_task(self.repo, self.given)
        self.assertEqual(cli.canonical_task(self.repo, None), self.canonical)

    def test_a_resume_never_overwrites_edits(self) -> None:
        cli.canonical_task(self.repo, self.given)
        self.canonical.write_text("edited")
        with self.assertRaisesRegex(SystemExit, "differs"):
            cli.canonical_task(self.repo, self.given)
        self.assertEqual(self.canonical.read_text(), "edited")
        self.assertEqual(cli.canonical_task(self.repo, self.canonical),
                         self.canonical)

    def test_no_task_at_all_is_an_error(self) -> None:
        with self.assertRaisesRegex(SystemExit, "no campaign task"):
            cli.canonical_task(self.repo, None)


class CampaignArtifactsTests(unittest.TestCase):
    """A campaign's artifact tree lives under `crustify/artifacts/`; one begun
    before the rename is still found under `crustify/campaigns/`."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

    def test_new_and_resumed_campaigns_live_under_artifacts(self) -> None:
        (self.repo / "crustify/artifacts/c1").mkdir(parents=True)
        self.assertEqual(cli.campaign_artifacts(self.repo, "c1"),
                         self.repo / "crustify/artifacts/c1")
        self.assertEqual(cli.campaign_artifacts(self.repo, "missing"),
                         self.repo / "crustify/artifacts/missing")

    def test_a_campaign_begun_before_the_rename_is_found(self) -> None:
        (self.repo / "crustify/campaigns/old").mkdir(parents=True)
        self.assertEqual(cli.campaign_artifacts(self.repo, "old"),
                         self.repo / "crustify/campaigns/old")
