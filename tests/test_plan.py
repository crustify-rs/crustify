from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from crustify import plan
from crustify.log_cost import kind


class PlanBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()
        self.out = self.repo / "crustify" / "artifacts" / "planning" / "run-1"
        self.out.mkdir(parents=True)

    def _batch(self, raw: object) -> Path:
        path = self.out / "batch.json"
        path.write_text(json.dumps(raw))
        return path

    def test_each_objective_loads(self) -> None:
        for objective in plan.OBJECTIVES:
            with self.subTest(objective=objective):
                self.assertEqual(plan.load_batch(self._batch({"objective": objective})),
                                 plan.PlanBatch(objective))

    def test_bad_batches_are_refused(self) -> None:
        for raw, needle in [({}, "missing batch field(s): objective"),
                            ({"objective": "amend"}, "must be one of emit, review"),
                            ({"objective": "emit", "items": []}, "unknown batch field(s): items"),
                            (["emit"], "must be a JSON object")]:
            with self.subTest(raw=raw), self.assertRaises(SystemExit) as cm:
                plan.load_batch(self._batch(raw))
            self.assertIn(needle, str(cm.exception))

    def test_dry_run_names_the_objective(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            plan.execute(self.repo, self._batch({"objective": "review"}),
                         output=self.out, dry_run=True)
        self.assertIn("objective review; no agent spawned", out.getvalue())

    def test_output_must_exist(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            plan.execute(self.repo, self._batch({"objective": "emit"}),
                         output=self.repo / "missing", dry_run=True)
        self.assertIn("--output must name an existing directory", str(cm.exception))

    def test_cost_buckets_each_arm(self) -> None:
        self.assertEqual((kind("plan-emit"), kind("plan-review")),
                         ("plan-emit", "plan-review"))


if __name__ == "__main__":
    unittest.main()
