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
                      "(subscription); no agent spawned", out.getvalue())

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
