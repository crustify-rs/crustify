"""Which optional skills each role carries, and how it is decided."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crustify import skills_config
from crustify.agents.orchestrate import OrchestrateAgent
from crustify.agents.translate import TranslateAgent

_KNOWN = ("wavefront", "ffibox", "audit")


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "skills-config.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, doc) -> Path:
        self.path.write_text(json.dumps(doc))
        return self.path

    def test_absent_file_takes_the_role_default(self) -> None:
        self.assertEqual(
            skills_config.selected(self.path, "translator", _KNOWN, _KNOWN),
            _KNOWN)

    def test_absent_role_takes_the_role_default(self) -> None:
        self._write({"orchestrator": []})
        self.assertEqual(
            skills_config.selected(self.path, "translator", _KNOWN, _KNOWN),
            _KNOWN)

    def test_empty_list_is_a_real_answer_not_an_absence(self) -> None:
        """The full-ablation arm: carry no optional skill at all."""
        self._write({"translator": []})
        self.assertEqual(
            skills_config.selected(self.path, "translator", _KNOWN, _KNOWN),
            ())

    def test_authored_order_is_preserved_and_repeats_collapse(self) -> None:
        self._write({"translator": ["ffibox", "wavefront", "ffibox"]})
        self.assertEqual(
            skills_config.selected(self.path, "translator", _KNOWN, _KNOWN),
            ("ffibox", "wavefront"))

    def test_comment_keys_are_not_roles(self) -> None:
        self._write({"_comment": ["prose"], "translator": []})
        self.assertEqual(skills_config.load(self.path), {"translator": []})

    def test_unknown_role_is_an_error(self) -> None:
        self._write({"auditor": []})
        with self.assertRaises(SystemExit):
            skills_config.load(self.path)

    def test_unknown_capability_is_an_error(self) -> None:
        """A typo must not silently render a narrower prompt."""
        self._write({"translator": ["wavefont"]})
        with self.assertRaises(SystemExit):
            skills_config.selected(self.path, "translator", _KNOWN, _KNOWN)

    def test_roles_cover_the_agent_classes_that_select(self) -> None:
        self.assertEqual(
            set(skills_config.ROLES),
            {TranslateAgent.skills_role, OrchestrateAgent.skills_role})


class CatalogTests(unittest.TestCase):
    def test_every_default_is_a_declared_capability(self) -> None:
        for cls in (TranslateAgent, OrchestrateAgent):
            with self.subTest(role=cls.skills_role):
                self.assertTrue(set(cls.DEFAULT_CAPABILITIES)
                                <= set(cls.CAPABILITIES))

    def test_the_shipped_spec_validates_against_both_catalogs(self) -> None:
        spec = Path(__file__).resolve().parent.parent / "specs/skills-config.json"
        for cls in (TranslateAgent, OrchestrateAgent):
            with self.subTest(role=cls.skills_role):
                self.assertEqual(
                    skills_config.selected(spec, cls.skills_role,
                                           tuple(cls.CAPABILITIES), ()),
                    cls.DEFAULT_CAPABILITIES)


if __name__ == "__main__":
    unittest.main()
