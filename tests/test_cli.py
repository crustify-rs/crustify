from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
              mock.patch.object(cli, "_handle_assist", record("assist")),
              mock.patch.object(cli, "_handle_spawn_worklist", record("spawn-worklist")),
              mock.patch.object(cli, "_handle_spawn_reviewer", record("spawn-reviewer")),
              mock.patch.object(cli, "_handle_spawn_planner", record("spawn-planner")),
              mock.patch.object(cli, "_handle_usage", record("usage"))):
            cli.main()
        return seen

    def test_a_workdir_opens_the_assistant(self) -> None:
        seen = self._run(str(self.repo), "--campaign", "wrap", "--start",
                         "--model", "openrouter/anthropic/claude-opus-5",
                         "--billing", "api")
        self.assertEqual(seen["handler"], "assist")
        self.assertEqual(seen["args"].workdir, str(self.repo))
        self.assertEqual(seen["args"].campaign, "wrap")
        self.assertTrue(seen["args"].start)
        self.assertEqual(config.MODEL_OVERRIDE, "openrouter/anthropic/claude-opus-5")
        self.assertEqual(config.BILLING, "api")

    def test_no_argument_opens_the_assistant_here(self) -> None:
        seen = self._run()
        self.assertEqual(seen["handler"], "assist")
        self.assertIsNone(seen["args"].workdir)          # the current directory
        self.assertFalse(seen["args"].start)

    def test_the_old_campaign_commands_are_gone(self) -> None:
        for command in ("translate", "audit"):
            with self.subTest(command=command), mock.patch("sys.stderr"), \
                    self.assertRaises(SystemExit):
                self._run(command, str(self.repo), str(self.task))

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
                         "crustify/artifacts/planner/run-2/task.json",
                         "--log-dir", "crustify/artifacts/planner/run-2", "--dry-run")
        self.assertEqual(seen["handler"], "spawn-planner")
        self.assertEqual(seen["args"].task,
                         Path("crustify/artifacts/planner/run-2/task.json"))
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

    def test_usage_needs_no_workdir(self) -> None:
        seen = self._run("usage", "a.transcript.jsonl", "b.transcript.jsonl")
        self.assertEqual(seen["handler"], "usage")
        self.assertEqual(len(seen["args"].files), 2)
        self.assertIsNone(seen["args"].output)

    def test_cost_is_folded_into_usage(self) -> None:
        """`cost` is no longer a command, so it opens the assistant on a
        workdir named `cost`, which takes no extra positional."""
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._run("cost", "a.usage.json", "b.usage.json")

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


class AssistantSettingsTests(unittest.TestCase):
    """`crustify [WORKDIR]` reads its campaign from crustify/CRUSTIFY.md; a
    directory without one gets none written: the assistant writes it in the
    repository it establishes, from the template or --settings."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.canonical = self.repo / "crustify/CRUSTIFY.md"

    def _install(self, campaign: str) -> None:
        template, _ = cli.detached_settings(None, campaign, lambda: None)
        self.canonical.parent.mkdir(parents=True, exist_ok=True)
        self.canonical.write_text(template.read_text())

    def test_a_missing_file_is_the_campaign_template_unwritten(self) -> None:
        for campaign in ("port", "wrap", "audit"):
            with self.subTest(campaign=campaign):
                task, got = cli.detached_settings(None, campaign, lambda: None)
                self.assertEqual((task.name, got), ("CRUSTIFY.template.md", campaign))
                self.assertFalse(self.canonical.exists())

    def test_the_file_decides_and_a_contradiction_is_refused(self) -> None:
        self._install("port")
        cli.campaign_settings(self.repo, None, "port", lambda: None)
        self.assertEqual(cli.campaign_settings(self.repo, None, None,
                                               lambda: None)[1], "port")
        with self.assertRaisesRegex(SystemExit, "configures a port campaign"):
            cli.campaign_settings(self.repo, None, "audit", lambda: None)

    def test_an_unanswered_campaign_is_asked_and_recorded(self) -> None:
        self.canonical.parent.mkdir(parents=True)
        self.canonical.write_text(
            "**Port or wrap?** (`id: campaign`)\n   - Answer: `<port | wrap>`\n")
        self.assertEqual(cli.campaign_settings(self.repo, None, None,
                                               lambda: "wrap")[1], "wrap")
        self.assertIn("- Answer: `wrap`", self.canonical.read_text())

    def test_a_file_without_the_question_takes_the_flag(self) -> None:
        """The bare ablation's file is the whole prompt and asks nothing."""
        self.canonical.parent.mkdir(parents=True)
        self.canonical.write_text("Audit this crate.\n")
        self.assertEqual(cli.campaign_settings(self.repo, None, "audit",
                                               lambda: None)[1], "audit")
        self.assertEqual(self.canonical.read_text(), "Audit this crate.\n")

    def test_nobody_to_ask_is_an_error(self) -> None:
        with self.assertRaisesRegex(SystemExit, "pass --campaign"):
            cli.detached_settings(None, None, lambda: None)
        self.assertFalse(self.canonical.exists())

    def test_detached_settings_write_nothing(self) -> None:
        task, campaign = cli.detached_settings(None, "port", lambda: None)
        self.assertEqual((task.name, campaign), ("CRUSTIFY.template.md", "port"))
        given = self.repo / "mine.md"
        given.write_text("**Port or wrap?** (`id: campaign`)\n   - Answer: `wrap`\n")
        self.assertEqual(cli.detached_settings(given, None, lambda: None),
                         (given.resolve(), "wrap"))
        with self.assertRaisesRegex(SystemExit, "configures a wrap campaign"):
            cli.detached_settings(given, "port", lambda: None)
        self.assertEqual(sorted(p.name for p in self.repo.iterdir()), ["mine.md"])

    def test_a_headless_session_without_settings_needs_them(self) -> None:
        args = SimpleNamespace(workdir=str(self.repo), start=True, settings=None,
                               campaign="wrap", task_only=False, resume=None)
        with mock.patch.object(sys.stdin, "isatty", return_value=False), \
                self.assertRaisesRegex(SystemExit, "pass --settings"):
            cli._handle_assist(args)
        self.assertFalse((self.repo / "crustify").exists())

    def test_a_headless_session_needs_start(self) -> None:
        args = SimpleNamespace(workdir=str(self.repo), start=False, settings=None,
                               campaign="wrap", task_only=False)
        with mock.patch.object(sys.stdin, "isatty", return_value=False), \
                self.assertRaisesRegex(SystemExit, "pass --start"):
            cli._handle_assist(args)

    def test_the_session_opens_idle_unless_started(self) -> None:
        from crustify.agents.assist import START, AssistAgent
        task, _ = cli.detached_settings(None, "wrap", lambda: None)
        for start, first in ((False, ""), (True, START)):
            with self.subTest(start=start):
                agent = AssistAgent(self.repo, kind="translate", task=task,
                                    model="anthropic/claude-opus-5", start=start)
                self.assertEqual(agent._prompt(), first)


class ResumeTests(unittest.TestCase):
    """`--resume` finds assistant sessions through the index in crustify's
    home, so it works from any directory."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_root = tmp.name
        self.home = Path(tmp.name) / "home"
        patcher = mock.patch.dict("os.environ", {"CRUSTIFY_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.a, self.b = Path(tmp.name) / "a", Path(tmp.name) / "b"
        sessions = self.home / "sessions"
        sessions.mkdir(parents=True)
        import json
        for sid, wd, at in (("s-1", self.a, "2026-10-19T10:00:00+00:00"),
                            ("s-2", self.a, "2026-10-19T11:00:00+00:00"),
                            ("s-3", self.b, "2026-10-19T09:00:00+00:00")):
            (sessions / f"{sid}.json").write_text(json.dumps({
                "session_id": sid, "workdir": str(wd), "started_at": at,
                "cli": "claude", "provider": "anthropic",
                "model": "claude-opus-5"}))

    def test_an_id_is_found_from_anywhere(self) -> None:
        self.assertEqual(cli.assistant_session(None, "s-3")["workdir"], str(self.b))

    def test_the_most_recent_session_of_a_workdir_or_of_all(self) -> None:
        self.assertEqual(cli.assistant_session(self.b, None)["session_id"], "s-3")
        self.assertEqual(cli.assistant_session(None, None)["session_id"], "s-2")

    def test_an_unknown_session_is_an_error(self) -> None:
        with self.assertRaisesRegex(SystemExit, "no assistant session s-9"):
            cli.assistant_session(None, "s-9")

    def test_the_assistant_indexes_its_sessions(self) -> None:
        import json
        from crustify.agents.assist import AssistAgent
        session = self.home / "sessions" / "c-4"
        agent = AssistAgent(self.a, kind="translate", task=self.a / "CRUSTIFY.md",
                            model="anthropic/claude-opus-5", checkout=None,
                            artifact_dir=session, log_stem="assistant-x")
        with agent._make_log() as log:
            log.session({"session_id": "s-4", "cli": "claude"})
        indexed = json.loads((session / "index.json").read_text())
        self.assertEqual((indexed["cwd"], indexed["workdir"], indexed["agent"]),
                         (str(self.a.resolve()), None, "assistant"))
        self.assertTrue(indexed["record"].endswith("assistant-x.session.json"))
        # The paths are the index's alone: the record, which the campaign
        # tracks once copied, carries none.
        record = json.loads((session / "assistant-x.session.json").read_text())
        self.assertNotIn("workdir", record)
        self.assertNotIn("cwd", record)

    def _session_dir(self, sid: str, cli_id: str, cwd: Path, at: str,
                     workdir: Path | None = None) -> Path:
        import json
        d = self.home / "sessions" / sid
        d.mkdir(parents=True)
        (d / "index.json").write_text(json.dumps({
            "session_id": cli_id, "cwd": str(cwd), "workdir": None,
            "dir": str(d), "started_at": at, "cli": "codex",
            "provider": "openai", "model": "gpt-5"}))
        if workdir is not None:
            (d / "workdir").write_text(f"{workdir}\n")
        return d

    def test_a_session_dir_is_found_by_either_id(self) -> None:
        d = self._session_dir("c-5", "codex-5", self.a, "2026-10-20T10:00:00+00:00")
        for sid in ("c-5", "codex-5"):
            with self.subTest(sid=sid):
                record = cli.assistant_session(None, sid)
                self.assertEqual((record["session_id"], record["dir"]), ("codex-5", str(d)))

    def test_a_created_checkout_is_found_by_its_path(self) -> None:
        clone = Path(self.tmp_root) / "clone"
        self._session_dir("c-6", "c-6", self.a, "2026-10-20T11:00:00+00:00", clone)
        record = cli.assistant_session(clone, None)
        self.assertEqual((record["session_id"], record["workdir"], record["cwd"]),
                         ("c-6", str(clone), str(self.a)))
        # Where it started finds it too: the most recent of that directory.
        self.assertEqual(cli.assistant_session(self.a, None)["session_id"], "c-6")


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

    def test_every_run_brings_the_plan_up_to_date(self) -> None:
        from crustify.agents.plan import PlanAgent
        agent = PlanAgent(self.repo)
        body = agent.system_preamble()
        self.assertEqual(agent.stage, "plan")
        self.assertIn(f"{self.repo.resolve()}/crustify/CRUSTIFY.md", body)
        self.assertIn("### 1. The committed plan", body)
        self.assertIn("Only a correction is a finding", body)
        self.assertIn("re-plan only waves that are `todo`", body)
        # The details of how to plan come from the included specs.
        self.assertIn("# Decomposition\n\nDecomposition turns", body)
        self.assertIn("# Scheduling\n\nScheduling turns", body)
        self.assertIn("under `crustify/reviews/planner/`", body)
        self.assertNotIn("objective: `", body)
        self.assertNotIn("scaffold", body.split("### 3. Planning")[1].split("### 4.")[0])
