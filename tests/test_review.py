"""The reviewer: its batch, its objectives, and how they shape its prompt."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import deps, review, translate
from crustify.agents.review import ReviewAgent

_COMMIT = "3f2a9c1"
_ITEM = {"name": "T", "defined_in": "include/t.h", "kind": "type",
         "field_anchors": [], "home": "crustify/rust/demo/src/t.rs"}


class _Checkouts:
    """Stand-in wavefront and ffibox checkouts; crustify resolves to itself.
    ``absent`` names dependencies that are not installed."""

    def __init__(self, test: unittest.TestCase, absent: tuple[str, ...] = ()):
        tmp = tempfile.TemporaryDirectory()
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for dep in ("wavefront", "ffibox"):
            (self.root / dep).mkdir()
            (self.root / dep / "SKILL.md").write_text(
                f"- Skill name: {dep}\n- Description: stand-in\n")
            (self.root / dep / "README.md").write_text(f"# {dep}\n")
        real = deps.dep_root

        def dep_root(name: str) -> Path:
            if name in absent:
                return self.root / "missing"
            return real(name) if name == "crustify" else self.root / name

        patcher = mock.patch.object(deps, "dep_root", side_effect=dep_root)
        patcher.start()
        test.addCleanup(patcher.stop)


class ReviewBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "batch.json"

    def load(self, doc: object) -> review.ReviewBatch:
        self.path.write_text(json.dumps(doc))
        return review.load_batch(self.path)

    def test_objectives_are_optional(self) -> None:
        batch = self.load({"commits": [_COMMIT]})
        self.assertIsNone(batch.objectives)
        self.assertEqual((batch.route, batch.commits), ("commits", [_COMMIT]))

    def test_objectives_are_carried(self) -> None:
        batch = self.load({"objectives": ["ub", "fix"], "commits": [_COMMIT]})
        self.assertEqual(batch.objectives, ["ub", "fix"])

    def test_a_translator_objective_is_not_a_review_field(self) -> None:
        with self.assertRaisesRegex(SystemExit, "unknown batch field"):
            self.load({"objective": "review", "commits": [_COMMIT]})

    def test_malformed_objectives_are_rejected(self) -> None:
        for objectives in ([], "ub", ["ub", "ub"], ["Ub"], [1]):
            with self.subTest(objectives=objectives), \
                    self.assertRaises(SystemExit):
                self.load({"objectives": objectives, "commits": [_COMMIT]})

    def test_commits_are_validated(self) -> None:
        for commits in ([], ["xyz1234"], ["abc"], [_COMMIT, _COMMIT], [1]):
            with self.subTest(commits=commits), self.assertRaises(SystemExit):
                self.load({"commits": commits})

    def test_c_items_are_not_a_review_worklist(self) -> None:
        with self.assertRaisesRegex(SystemExit, "unknown batch field"):
            self.load({"items": [_ITEM]})

    def test_an_audit_reviews_modules(self) -> None:
        modules = ["src/frame.rs",
                   {"path": "src/codec.rs", "types": ["Decoder"],
                    "trait_impls": ["Drop for Decoder",
                                    "From<Oid> for String",
                                    "Iterator for Packets<'_>"],
                    "functions": ["open_input", "util::probe"]}]
        batch = self.load({"modules": modules})
        self.assertEqual((batch.route, batch.modules), ("modules", modules))
        self.assertEqual(batch.commits, [])

    def test_commits_and_modules_are_exclusive(self) -> None:
        with self.assertRaisesRegex(SystemExit, "not both"):
            self.load({"commits": [_COMMIT], "modules": ["src/a.rs"]})

    def test_a_batch_needs_a_worklist_or_reports(self) -> None:
        with self.assertRaisesRegex(SystemExit, "commits, modules or reports"):
            self.load({"objectives": ["ub"]})

    def test_modules_are_validated(self) -> None:
        for modules in ([], ["/abs.rs"], ["../out.rs"], ["a.rs", "a.rs"], [""],
                        [{"path": "a.rs"}], [{"path": "a.rs", "types": []}],
                        [{"path": "a.rs", "types": ["Bad name"]}],
                        [{"path": "a.rs", "trait_impls": ["Drop"]}],
                        [{"path": "a.rs", "trait_impls": ["Drop for "]}],
                        [{"path": "a.rs", "trait_impls": ["Drop for T",
                                                          "Drop for T"]}],
                        [{"path": "a.rs", "items": ["T"]}],
                        ["a.rs", {"path": "a.rs", "types": ["T"]}]):
            with self.subTest(modules=modules), self.assertRaises(SystemExit):
                self.load({"modules": modules})

    def test_reports_come_exactly_with_revisit(self) -> None:
        report = "crustify/reviews/b/ub_safe/x"
        batch = self.load({"objectives": ["revisit", "fix"], "reports": [report]})
        self.assertEqual((batch.route, batch.reports), ("reports", [report]))
        with self.assertRaisesRegex(SystemExit, "revisit"):
            self.load({"objectives": ["ub"], "modules": ["a.rs"],
                       "reports": [report]})
        with self.assertRaisesRegex(SystemExit, "revisit"):
            self.load({"objectives": ["revisit"], "modules": ["a.rs"]})

    def test_the_translator_no_longer_reviews(self) -> None:
        self.path.write_text(json.dumps({"objective": "review", "items": [_ITEM]}))
        with self.assertRaisesRegex(SystemExit, "spawn-reviewer"):
            translate.load_batch(self.path)


class ReviewAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        (self.repo / "crustify").mkdir()

    def agent(self, objectives: list[str] | None) -> ReviewAgent:
        return ReviewAgent(self.repo, route="commits", commits=[_COMMIT],
                           objectives=objectives, git_base="review-wave-0",
                           artifact_dir=self.repo, log_stem="reviewer")

    def test_skills_contribute_their_objectives(self) -> None:
        _Checkouts(self)
        self.assertEqual(
            self.agent(None).available_objectives(),
            ["lifecycle", "unsafety", "contracts", "ub", "equiv", "internal",
             "conventions", "misc", "coverage", "revisit", "disclose", "fix"])

    def test_revisit_runs_by_default_only_with_reports(self) -> None:
        _Checkouts(self)
        self.assertNotIn("revisit", self.agent(None).objectives)
        agent = ReviewAgent(self.repo, route="reports",
                            reports=["crustify/reviews/b/ub_safe/x"],
                            objectives=None, git_base="review-wave-0",
                            artifact_dir=self.repo, log_stem="reviewer")
        self.assertIn("revisit", agent.objectives)
        self.assertIn("crustify/reviews/b/ub_safe/x", agent.system_preamble())

    def test_an_absent_skill_takes_its_objective_with_it(self) -> None:
        """A reviewer pointed at a crate wavefront does not describe is never
        asked about lifecycle primitives."""
        _Checkouts(self, absent=("wavefront",))
        agent = self.agent(None)
        self.assertNotIn("lifecycle", agent.available_objectives())
        with self.assertRaisesRegex(SystemExit, "lifecycle"):
            self.agent(["lifecycle"])

    def test_unknown_objectives_are_rejected(self) -> None:
        _Checkouts(self)
        with self.assertRaisesRegex(SystemExit, "boundary"):
            self.agent(["boundary"])

    def test_enabling_is_decided_in_prose(self) -> None:
        """Every section stays in the prompt; the objectives line tells the
        agent which ones to review for."""
        _Checkouts(self)
        pre = self.agent(["ub", "lifecycle"]).system_preamble()
        self.assertIn("objectives: `lifecycle, ub`", pre)
        self.assertIn("skip what the steps say about the others", pre)
        self.assertIn("#### Equivalence (`equiv`)", pre)
        self.assertNotIn("OBJECTIVE", pre)

    def test_every_objective_has_a_section_headed_by_its_id(self) -> None:
        """The objectives are declared in code and described in prose; this
        keeps the two in step."""
        from crustify.agents.base import _PKG_ROOT
        from crustify.agents.review import OBJECTIVES, SKILL_OBJECTIVES
        text = (_PKG_ROOT / "prompts" / "reviewer.md").read_text()
        for objective in OBJECTIVES:
            if objective == "fix":
                continue
            with self.subTest(objective=objective):
                self.assertRegex(text, rf"\n#{{3,4}} .+ \(`{objective}`\)\n")
        for skill, objectives in SKILL_OBJECTIVES.items():
            header = (_PKG_ROOT / "prompts" / "skills" / skill
                      / "reviewer.md").read_text()
            for objective in objectives:
                with self.subTest(skill=skill, objective=objective):
                    self.assertRegex(header, rf"\n#{{3,4}} .+ \(`{objective}`\)\n")

    def test_fix_is_decided_in_prose(self) -> None:
        """`fix` gates no section: the prompt states both cases, and the
        objectives line tells the agent which one holds."""
        _Checkouts(self)
        for objectives, line in ((["ub"], "objectives: `ub`"),
                                 (["ub", "fix"], "objectives: `ub, fix`")):
            with self.subTest(objectives=objectives):
                pre = self.agent(objectives).system_preamble()
                self.assertIn(line, pre)
                self.assertIn("If `fix` is enabled, patch every finding", pre)
                self.assertIn("If `fix` is not enabled, skip this step", pre)

    def test_testing_says_when_gates_run_the_prompts_who_runs_them(self) -> None:
        from crustify.agents.base import _PKG_ROOT, deps
        testing = (deps.CHECKOUT / "docs/translate/howto/testing.md").read_text()
        self.assertIn("BSan, when available, is run for every batch and at subsystem end",
                      testing)
        self.assertIn("Miri is run after every wave", testing)
        self.assertNotIn("review batch", testing)
        reviewer = (_PKG_ROOT / "prompts" / "reviewer.md").read_text()
        self.assertIn("so you own its gates", reviewer)
        translator = (_PKG_ROOT / "prompts" / "translator.md").read_text()
        self.assertIn("belong to the review that follows", translator)

    def test_the_reviewer_is_handed_the_conventions_and_how_tos(self) -> None:
        """The standard a reviewer judges by is the text the translator
        followed, word for word; the prompt tells it to ignore the
        conventions outside a Crustify-generated batch."""
        _Checkouts(self)
        pre = self.agent(None).system_preamble()
        for heading in ("# Crustify coding conventions",
                        "# Generating safe bindings", "# Porting", "# Testing",
                        "# Landing"):
            with self.subTest(heading=heading):
                self.assertIn(heading, pre)
        self.assertIn("otherwise, ignore them", pre)

    def test_the_stage_keeps_the_review_cost_buckets(self) -> None:
        _Checkouts(self)
        from crustify.log_cost import kind
        stage = self.agent(None).stage
        self.assertEqual(stage, f"review-commits_{_COMMIT}")
        self.assertEqual(kind(stage), "review-commits")
        modules = ReviewAgent(self.repo, route="modules", modules=["src/a.rs"],
                              objectives=None, git_base="w",
                              artifact_dir=self.repo, log_stem="reviewer")
        self.assertEqual(kind(modules.stage), "review-modules")
        self.assertIn(_COMMIT, self.agent(None).system_preamble())


class ExecuteTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        (self.repo / "crustify").mkdir()
        self.output = self.repo / "out"
        self.output.mkdir()
        self.batch = self.repo / "batch.json"
        _Checkouts(self)

    def test_dry_run_lists_the_resolved_objectives(self) -> None:
        self.batch.write_text(json.dumps(
            {"objectives": ["fix", "ub"], "commits": [_COMMIT]}))
        with mock.patch("builtins.print") as printed:
            review.execute(self.repo, self.batch, base_branch="review-wave-0",
                           output=self.output, dry_run=True)
        self.assertIn("objectives ub, fix", printed.call_args.args[0])

    def test_dry_run_rejects_an_objective_no_skill_offers(self) -> None:
        self.batch.write_text(json.dumps(
            {"objectives": ["nonesuch"], "commits": [_COMMIT]}))
        with self.assertRaisesRegex(SystemExit, "nonesuch"):
            review.execute(self.repo, self.batch, base_branch="review-wave-0",
                           output=self.output, dry_run=True)

    def test_artifacts_take_the_reviewer_names(self) -> None:
        self.batch.write_text(json.dumps({"commits": [_COMMIT]}))
        seen = {}

        def run(agent):
            seen.update(stem=agent.log_stem, dir=agent.artifact_dir)

        with mock.patch.object(ReviewAgent, "run", run), \
                mock.patch("builtins.print"):
            review.execute(self.repo, self.batch, base_branch="review-wave-0",
                           output=self.output)
        self.assertEqual(seen, {"stem": "reviewer", "dir": self.output})


if __name__ == "__main__":
    unittest.main()
