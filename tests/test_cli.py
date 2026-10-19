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
        self.task = self.repo / "CRUSTIFY.md"
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
              mock.patch.object(cli, "_handle_spawn_planner", record("spawn-planner")),
              mock.patch.object(cli, "_handle_cost", record("cost"))):
            cli.main()
        return seen

    def test_translate_starts_the_translation_orchestrator(self) -> None:
        seen = self._run("translate", str(self.repo), str(self.task),
                         "--model", "openrouter/anthropic/claude-opus-5",
                         "--billing", "api")
        self.assertEqual(seen["handler"], "orchestrate")
        self.assertEqual(seen["args"].kind, "translate")
        self.assertEqual(config.MODEL_OVERRIDE, "openrouter/anthropic/claude-opus-5")
        self.assertEqual(config.BILLING, "api")

    def test_audit_starts_the_audit_orchestrator(self) -> None:
        seen = self._run("audit", str(self.repo), str(self.task), "--task-only")
        self.assertEqual(seen["handler"], "orchestrate")
        self.assertEqual(seen["args"].kind, "audit")
        self.assertTrue(seen["args"].task_only)

    def test_spawn_translator_runs_one_task(self) -> None:
        seen = self._run("spawn-translator", str(self.repo), "task.json",
                         "--log-dir", "out")
        self.assertEqual(seen["handler"], "spawn-worklist")
        self.assertEqual(seen["args"].role, "translator")
        self.assertEqual(seen["args"].task, Path("task.json"))

    def test_spawn_binder_runs_one_task(self) -> None:
        seen = self._run("spawn-binder", str(self.repo), "task.json",
                         "--log-dir", "out")
        self.assertEqual(seen["args"].log_dir, Path("out"))
        self.assertEqual(seen["handler"], "spawn-worklist")
        self.assertEqual(seen["args"].role, "binder")

    def test_spawn_reviewer_runs_one_review_task(self) -> None:
        seen = self._run("spawn-reviewer", str(self.repo), "task.json",
                         "--log-dir", "out", "--dry-run")
        self.assertEqual(seen["handler"], "spawn-reviewer")
        self.assertTrue(seen["args"].dry_run)

    def test_spawn_planner_runs_one_planner(self) -> None:
        seen = self._run("spawn-planner", str(self.repo),
                         "crustify/artifacts/planning/run-2/task.json",
                         "--log-dir", "crustify/artifacts/planning/run-2", "--dry-run")
        self.assertEqual(seen["handler"], "spawn-planner")
        self.assertEqual(seen["args"].task,
                         Path("crustify/artifacts/planning/run-2/task.json"))
        self.assertTrue(seen["args"].dry_run)

    def test_a_spawned_agent_takes_its_settings_from_its_task(self) -> None:
        """Model, billing and branch live in task.json, so the spawn commands
        no longer accept them as flags; the log dir is still a flag, and a
        required one."""
        for command in ("spawn-binder", "spawn-translator", "spawn-reviewer",
                        "spawn-planner"):
            for flag in (("--model", "openai/gpt-5.6"), ("--billing", "api"),
                         ("--base-branch", "wave"), ("--output", "out"), ()):
                with self.subTest(command=command, flag=flag[:1]), \
                        mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                    self._run(command, str(self.repo), "task.json", *flag,
                              *(("--log-dir", "out") if flag else ()))

    def test_spawn_planner_needs_a_campaign_tree(self) -> None:
        bare = self.repo / "bare"
        bare.mkdir()
        with self.assertRaises(SystemExit):
            self._run("spawn-planner", str(bare), "task.json")

    def test_spawn_reviewer_needs_a_campaign_tree(self) -> None:
        bare = self.repo / "bare"
        bare.mkdir()
        with self.assertRaises(SystemExit):
            self._run("spawn-reviewer", str(bare), "task.json")

    def test_spawn_auditor_is_gone(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._run("spawn-auditor", str(self.repo))

    def test_there_is_no_campaign_id(self) -> None:
        """A repository holds one cumulative campaign: rerunning resumes it."""
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._run("translate", str(self.repo), str(self.task),
                      "--campaign", "x")

    def test_cost_needs_no_workdir(self) -> None:
        seen = self._run("cost", "a.usage.json", "b.usage.json")
        self.assertEqual(seen["handler"], "cost")
        self.assertEqual(len(seen["args"].usage), 2)

    def test_spawn_translator_needs_a_campaign_tree(self) -> None:
        bare = self.repo / "bare"
        bare.mkdir()
        with self.assertRaises(SystemExit):
            self._run("spawn-translator", str(bare), "task.json")

    def test_old_spellings_are_rejected(self) -> None:
        for argv in (
                (str(self.repo), "orchestrate-translation", str(self.task)),
                ("--model", "x", "translate", str(self.repo), str(self.task)),
                (str(self.repo), "audit", "unsafe")):
            with self.subTest(argv=argv), mock.patch("sys.stderr"), \
                    self.assertRaises(SystemExit):
                self._run(*argv)


class CanonicalTaskTests(unittest.TestCase):
    """The orchestrator reads its settings from `<workdir>/crustify/CRUSTIFY.md`."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.given = self.repo / "given.md"
        self.given.write_text("answers")
        self.canonical = self.repo / "crustify/CRUSTIFY.md"

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
        with self.assertRaisesRegex(SystemExit, "no campaign settings"):
            cli.canonical_task(self.repo, None)


class PlannerPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()

    def test_the_prompt_carries_its_objective(self) -> None:
        from crustify.agents.plan import PlanAgent
        for objective in ("emit", "review"):
            with self.subTest(objective=objective):
                agent = PlanAgent(self.repo, objective=objective)
                body = agent.system_preamble()
                self.assertIn(f"- objective: `{objective}`", body)
                self.assertEqual(agent.stage, f"plan-{objective}")
        self.assertIn(f"{self.repo.resolve()}/crustify/CRUSTIFY.md", body)
        self.assertIn("#### Emit (`emit`)", body)
        self.assertIn("#### Review (`review`)", body)
        self.assertIn("under `crustify/reviews/planner/`", body)
        self.assertNotIn("scaffold", body.split("### 3. Planning")[1].split("### 4.")[0])

    def test_an_unknown_objective_is_refused(self) -> None:
        from crustify.agents.plan import PlanAgent
        with self.assertRaises(SystemExit):
            PlanAgent(self.repo, objective="amend")
