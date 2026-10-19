from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from crustify import plan
from crustify.translate import RunSettings

RUN = {"model": "anthropic/claude-opus-5", "billing": "subscription"}


class PlanBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()
        self.out = self.repo / "crustify" / "artifacts" / "planning" / "run-1"
        self.out.mkdir(parents=True)

    def _batch(self, raw: object, *, complete: bool = True) -> Path:
        if complete and isinstance(raw, dict):
            raw = {**RUN, **raw}
        path = self.out / "task.json"
        path.write_text(json.dumps(raw))
        return path

    def test_each_objective_loads(self) -> None:
        for objective in plan.OBJECTIVES:
            with self.subTest(objective=objective):
                self.assertEqual(plan.load_batch(self._batch({"objective": objective})),
                                 plan.PlanBatch(objective, RunSettings(**RUN)))

    def test_bad_batches_are_refused(self) -> None:
        for raw, needle in [({}, "missing task field(s): objective"),
                            ({"objective": "amend"}, "must be one of emit, review"),
                            ({"objective": "emit", "items": []}, "unknown task field(s): items"),
                            ({"objective": "emit", "base_branch": "x"},
                             "unknown task field(s): base_branch"),
                            (["emit"], "must be a JSON object")]:
            with self.subTest(raw=raw), self.assertRaises(SystemExit) as cm:
                plan.load_batch(self._batch(raw))
            self.assertIn(needle, str(cm.exception))
        with self.assertRaises(SystemExit) as cm:
            plan.load_batch(self._batch({"objective": "emit"}, complete=False))
        self.assertIn("missing task field(s): billing, model", str(cm.exception))


    def test_dry_run_names_the_objective(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            plan.execute(self.repo, self._batch({"objective": "review"}),
                         log_dir=self.out, dry_run=True)
        self.assertIn("objective review; model anthropic/claude-opus-5 "
                      "(subscription); no additional instructions; no agent spawned",
                      out.getvalue())

    def test_instructions_are_read_beside_the_task(self) -> None:
        (self.out / "instructions.md").write_text("\nRe-plan libavutil only.\n")
        batch = plan.load_batch(self._batch({"objective": "emit",
                                             "instructions": "instructions.md"}))
        self.assertEqual(batch.instructions.path, (self.out / "instructions.md").resolve())
        self.assertEqual(batch.instructions.text, "Re-plan libavutil only.")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            plan.execute(self.repo, self._batch({"objective": "emit",
                                                 "instructions": "instructions.md"}),
                         log_dir=self.out, dry_run=True)
        self.assertIn("additional instructions from "
                      f"{(self.out / 'instructions.md').resolve()}", out.getvalue())

    def test_bad_instructions_are_refused(self) -> None:
        (self.out / "empty.md").write_text("  \n")
        for value, needle in [("missing.md", "cannot read instructions"),
                              ("empty.md", "instructions file is empty"),
                              ("", "instructions must name a file"),
                              (["a.md"], "instructions must name a file")]:
            with self.subTest(value=value), self.assertRaises(SystemExit) as cm:
                plan.load_batch(self._batch({"objective": "emit", "instructions": value}))
            self.assertIn(needle, str(cm.exception))

    def test_instructions_close_the_system_prompt(self) -> None:
        from crustify.agents.plan import PlanAgent
        from crustify.translate import Instructions

        agent = PlanAgent(self.repo, objective="emit")
        empty = agent.system_preamble()
        self.assertIn("## Additional instructions", empty)
        self.assertNotIn("<!-- INSTRUCTIONS -->", empty)
        agent.instructions = Instructions(self.out / "instructions.md",
                                          "Re-plan {libavutil} only.")
        filled = agent.system_preamble()
        # The text fills the prompt's own section, braces and all, and the
        # CLI adds nothing else.
        self.assertEqual(filled.replace("Re-plan {libavutil} only.", ""), empty)

    def test_every_spawned_role_prompt_takes_instructions(self) -> None:
        from crustify.agents.base import _PKG_ROOT, INSTRUCTIONS_MARKER

        for role in ("planner", "binder", "translator", "reviewer"):
            with self.subTest(role=role):
                text = (_PKG_ROOT / "prompts" / f"{role}.md").read_text()
                self.assertEqual(text.count(INSTRUCTIONS_MARKER), 1)
                self.assertLess(text.index("## Additional instructions"),
                                text.index(INSTRUCTIONS_MARKER))

    def test_log_dir_must_exist(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            plan.execute(self.repo, self._batch({"objective": "emit"}),
                         log_dir=self.repo / "missing", dry_run=True)
        self.assertIn("--log-dir must name an existing directory", str(cm.exception))

    def test_the_session_names_the_planner(self) -> None:
        from crustify.agents.plan import PlanAgent
        self.assertEqual(PlanAgent.role, "planner")


if __name__ == "__main__":
    unittest.main()
