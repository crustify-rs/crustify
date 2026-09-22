"""Discovery is the whole skill-selection mechanism."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from crustify import deps
from crustify.agents.base import _PKG_ROOT
from crustify.agents.orchestrate import OrchestrateAgent
from crustify.agents.translate import TranslateAgent

_ROLES = (TranslateAgent, OrchestrateAgent)


class DeclaredPathTests(unittest.TestCase):
    """A misspelled path ablates silently at run time, by design. It is a
    source bug rather than an operator mistake, so it is caught here."""

    def test_every_role_header_exists(self) -> None:
        for cls in _ROLES:
            for spec in cls.SKILLS:
                if spec.role_header is None:
                    continue
                with self.subTest(role=cls.name, header=spec.role_header):
                    self.assertTrue(
                        (_PKG_ROOT / "prompts" / spec.role_header).is_file())

    def test_every_in_tree_skill_file_exists(self) -> None:
        """Skills owned by this distribution, as opposed to the wavefront and
        ffibox checkouts, which a bare test environment need not have."""
        for cls in _ROLES:
            for spec in cls.SKILLS:
                if spec.dep != "crustify":
                    continue
                with self.subTest(role=cls.name, path=spec.path):
                    self.assertTrue((deps.CHECKOUT / spec.path).is_file())

    def test_the_role_skill_is_not_a_capability(self) -> None:
        """The first skill is what makes the agent that role, so it carries no
        capability name and nothing selects it."""
        for cls in _ROLES:
            with self.subTest(role=cls.name):
                self.assertIsNone(cls.SKILLS[0].capability)
                self.assertTrue(
                    all(s.capability for s in cls.SKILLS[1:]))

    def test_role_headers_follow_the_directory_layout(self) -> None:
        """`skills/<skill>/<role>.md`, one directory per skill and one file
        per role. The layout is what gives an ablation two grains, so a spec
        that spells its path some other way silently loses the coarse one."""
        for cls, role in ((TranslateAgent, "translator"),
                          (OrchestrateAgent, "orchestrator")):
            for spec in cls.SKILLS:
                if spec.role_header is None:
                    continue
                with self.subTest(role=role, header=spec.role_header):
                    self.assertEqual(
                        spec.role_header, f"skills/{spec.capability}/{role}.md")

    def test_a_self_contained_skill_carries_its_own_metadata(self) -> None:
        """A skill with no generic file to wrap must be frontmatter, or the
        renderer emits its name and description and nothing points at the
        body — the procedure would never reach the agent."""
        for cls in _ROLES:
            for spec in cls.SKILLS:
                if spec.role_header is not None:
                    continue
                with self.subTest(role=cls.name, path=spec.path):
                    text = (deps.CHECKOUT / spec.path).read_text()
                    self.assertTrue(
                        text.startswith("---") or "Doc path:" in text)

    def test_a_skill_directory_holds_every_role_that_carries_it(self) -> None:
        """The inverse: nothing sits in prompts/skills/ that no role reads."""
        declared = {
            (spec.capability or spec.path.rsplit("/", 2)[-2], role)
            for cls, role in ((TranslateAgent, "translator"),
                              (OrchestrateAgent, "orchestrator"))
            for spec in cls.SKILLS
        }
        root = _PKG_ROOT / "prompts" / "skills"
        on_disk = {(f.parent.name, f.stem) for f in root.glob("*/*.md")}
        self.assertEqual(on_disk, declared)

    def test_every_capability_is_ablatable_by_deleting_one_file(self) -> None:
        """Each optional skill is governed by exactly one file under
        prompts/skills/<capability>/<role>.md — its role header when it wraps
        a generic skill, its own path when it is self-contained. Without one,
        a skill shipped inside this distribution could not be removed from a
        prompt without uninstalling crustify."""
        for cls, role in ((TranslateAgent, "translator"),
                          (OrchestrateAgent, "orchestrator")):
            for spec in cls.SKILLS[1:]:
                with self.subTest(role=role, cap=spec.capability):
                    governing = spec.role_header or spec.path
                    self.assertTrue(
                        governing.endswith(
                            f"prompts/skills/{spec.capability}/{role}.md")
                        or governing == f"skills/{spec.capability}/{role}.md",
                        governing)


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parent
        self.agent = OrchestrateAgent(
            self.repo, kind="translate", task=Path(__file__),
            model="anthropic/claude-opus-5", workdir=self.repo)

    def test_a_present_skill_is_carried(self) -> None:
        self.assertIn("audit", self.agent.prompt_capabilities())

    def test_deleting_a_role_header_ablates_that_skill(self) -> None:
        real = Path.is_file
        header = _PKG_ROOT / "prompts" / "skills/audit/orchestrator.md"
        with mock.patch.object(
                Path, "is_file",
                lambda p: False if p == header else real(p)):
            agent = OrchestrateAgent(
                self.repo, kind="translate", task=Path(__file__),
                model="anthropic/claude-opus-5", workdir=self.repo)
            self.assertNotIn("audit", agent.prompt_capabilities())

    def test_an_uninstalled_dependency_ablates_its_skill(self) -> None:
        """The other half of the same rule: a generic skill lives in a
        checkout, and not installing the checkout removes it."""
        with mock.patch.object(deps, "dep_root",
                               return_value=Path("/nonexistent")):
            agent = OrchestrateAgent(
                self.repo, kind="translate", task=Path(__file__),
                model="anthropic/claude-opus-5", workdir=self.repo)
            self.assertEqual(agent.skill_specs(), ())

    def test_the_ablation_control_carries_no_skills(self) -> None:
        agent = OrchestrateAgent(
            self.repo, kind="translate", task=Path(__file__),
            model="anthropic/claude-opus-5", workdir=self.repo,
            task_only=True)
        self.assertEqual(agent.skill_specs(), ())
        self.assertEqual(agent.system_preamble(), "")


if __name__ == "__main__":
    unittest.main()
