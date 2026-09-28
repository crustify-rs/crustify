"""Discovery is the whole skill-selection mechanism."""
from __future__ import annotations

import collections
import re
import tempfile
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

    def test_a_role_skill_comes_first_and_is_not_a_capability(self) -> None:
        """A role skill is what makes the agent that role, so it carries no
        capability name and nothing selects it. An agent may have none — the
        orchestrator's was its playbook, which is now its prompt."""
        for cls in _ROLES:
            with self.subTest(role=cls.name):
                plain = [i for i, s in enumerate(cls.SKILLS)
                         if s.capability is None]
                self.assertIn(plain, ([], [0]))

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

    def test_every_declared_doc_path_resolves(self) -> None:
        """A `Doc path` is followed by the agent but decides no discovery, so
        a broken one is a dead instruction rather than an ablation."""
        from crustify.agents.base import _skill_meta
        for cls in _ROLES:
            for spec in cls.SKILLS:
                if spec.dep != "crustify":
                    continue
                _, _, _, doc = _skill_meta(deps.CHECKOUT / spec.path)
                with self.subTest(role=cls.name, path=spec.path):
                    self.assertTrue(doc is None or doc.is_file(), doc)

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
            for spec in cls.SKILLS:
                if spec.capability is None:
                    continue
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
            model="anthropic/claude-opus-5")

    def test_a_present_skill_is_carried(self) -> None:
        self.assertIn("sanitizers", self.agent.prompt_capabilities())

    def test_deleting_a_skills_file_ablates_it(self) -> None:
        """For a self-contained skill the file IS the skill, so its own path
        is what decides presence; a wrapped one is decided by its role header
        instead. Both are one file under prompts/skills/."""
        real = Path.exists
        skill = (deps.CHECKOUT
                 / "src/crustify/prompts/skills/sanitizers/orchestrator.md")
        with mock.patch.object(
                Path, "exists",
                lambda p: False if p == skill else real(p)):
            agent = OrchestrateAgent(
                self.repo, kind="translate", task=Path(__file__),
                model="anthropic/claude-opus-5")
            self.assertNotIn("sanitizers", agent.prompt_capabilities())

    def test_an_uninstalled_dependency_ablates_its_skill(self) -> None:
        """The other half of the same rule: a generic skill lives in a
        checkout, and not installing the checkout removes it."""
        with mock.patch.object(deps, "dep_root",
                               return_value=Path("/nonexistent")):
            agent = OrchestrateAgent(
                self.repo, kind="translate", task=Path(__file__),
                model="anthropic/claude-opus-5")
            self.assertEqual(agent.skill_specs(), ())

    def test_the_ablation_control_carries_no_skills(self) -> None:
        agent = OrchestrateAgent(
            self.repo, kind="translate", task=Path(__file__),
            model="anthropic/claude-opus-5",
            task_only=True)
        self.assertEqual(agent.skill_specs(), ())
        self.assertEqual(agent.system_preamble(), "")


class PromptRenderTests(unittest.TestCase):
    """`run()` calls `prompt.format(**arguments)`, so a stage prompt holding
    literal braces must escape them. The orchestrator's does, since its body
    is the campaign playbook and that documents a directory tree."""

    def test_every_stage_prompt_survives_format(self) -> None:
        """Any placeholder resolves here; what is under test is that no
        unescaped literal brace makes `format` raise."""
        for path in (_PKG_ROOT / "prompts").glob("*.md"):
            with self.subTest(prompt=path.name):
                path.read_text().format_map(collections.defaultdict(str))

    def test_the_coding_conventions_doc_resolves(self) -> None:
        """`_render_conventions` returns "" for an absent file, so a rename
        that misses `_conventions_md` deletes the conventions from every
        agent's system prompt and nothing raises."""
        for cls in _ROLES:
            with self.subTest(role=cls.name):
                agent = object.__new__(cls)
                self.assertTrue(cls._conventions_md(agent).is_file())


class PromptArgumentTests(unittest.TestCase):
    """Every supplied argument is used, and every used one is supplied.

    The two failures are asymmetric: a placeholder with no argument raises
    KeyError at launch, loudly. An argument no placeholder names is silently
    dead, and stays dead until someone audits it.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    #: Supplied to every agent by `CrustifyAgent._arguments`; a role that does
    #: not name one is not carrying a dead key, it is just not using shared
    #: infrastructure.
    _BASE = {"workdir", "git_base"}

    def _declared(self, body: str) -> set[str]:
        return set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", body))

    def _check(self, agent) -> None:
        declared, supplied = self._declared(agent._body()), set(agent._arguments())
        self.assertEqual(declared - supplied, set(), "placeholder with no argument")
        self.assertEqual(supplied - declared - self._BASE, set(),
                         "argument no placeholder names")

    def test_translator_arguments_match_its_placeholders(self) -> None:
        agent = TranslateAgent(
            self.repo, route="type",
            items=[{"name": "T", "defined_in": "a.h", "kind": "type",
                    "field_anchors": [], "home": "crustify/rust/x/src/a.rs"}],
            objective="wrap", git_base="wave-0",
            artifact_dir=self.repo, log_stem="x")
        self._check(agent)

    def test_orchestrator_arguments_match_its_placeholders(self) -> None:
        task = self.repo / "TASK.md"
        task.write_text("- Answer: none")
        agent = OrchestrateAgent(self.repo, kind="translate", task=task,
                                 model="anthropic/claude-opus-5")
        self._check(agent)


class OrchestratorPromptTests(unittest.TestCase):
    """The orchestrator's whole prompt rides the system slot."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()
        self.task = self.repo / "TASK.md"
        self.task.write_text("1. **Q** (`id: source`)\n   - Answer: `{brace}`")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _agent(self, **kw):
        return OrchestrateAgent(self.repo, kind="translate", task=self.task,
                                model="anthropic/claude-opus-5", **kw)

    def test_the_task_replaces_its_anchor(self) -> None:
        pre = self._agent().system_preamble()
        self.assertNotIn("<!-- TASK -->", pre)
        self.assertIn("`{brace}`", pre)

    def test_a_task_with_braces_survives_formatting(self) -> None:
        """The task is arbitrary user text spliced into a body that `format`
        then runs over, so its braces must be escaped on the way in."""
        self.task.write_text("- Answer: `{max_loc: 500}`")
        self.assertIn("`{max_loc: 500}`", self._agent().system_preamble())

    def test_the_user_turn_carries_no_instruction(self) -> None:
        """Everything the agent is told is in the system slot; neither backend
        accepts an empty positional, which is all the user turn is for."""
        agent = self._agent()
        self.assertLess(len(agent._prompt()), 100)
        self.assertGreater(len(agent.system_preamble()), 10_000)

    def test_a_missing_anchor_is_an_error(self) -> None:
        """Without it the task would vanish from the prompt in silence."""
        agent = self._agent()
        with mock.patch.object(Path, "read_text", lambda self: "no anchor"):
            with self.assertRaises(SystemExit):
                agent._body()

    def test_the_ablation_arm_contributes_nothing(self) -> None:
        agent = self._agent(task_only=True)
        self.assertEqual(agent.system_preamble(), "")
        self.assertEqual(agent.skill_specs(), ())


if __name__ == "__main__":
    unittest.main()
