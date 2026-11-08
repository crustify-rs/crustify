"""The tool specs under specs/tools/, and how the prompts include them."""
from __future__ import annotations

import collections
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import deps, translate
from crustify.agents.base import (
    _INCLUDE_RE, _PKG_ROOT, TOOLS_DIR, expand_includes, included_tools,
)
from crustify.agents.assist import CAMPAIGN_MARKER, AssistAgent, campaign_prompt
from crustify.agents.plan import PlanAgent
from crustify.agents.review import ReviewAgent
from crustify.agents.bind import BindAgent
from crustify.agents.translate import TranslateAgent

_TOOLS = deps.CHECKOUT / TOOLS_DIR


def _templates() -> dict[str, str]:
    """Every prompt template, the assistant's once per campaign kind."""
    out = {path.name: path.read_text()
           for path in (_PKG_ROOT / "prompts").glob("*.md")
           if path.name != "assistant.md"}
    for kind in ("translate", "audit"):
        out[f"{kind}-assistant"] = campaign_prompt(kind)
    return out


class ToolSpecTests(unittest.TestCase):
    """A tool spec is a header, `specs/tools/<tool>.md`, or an augmentation,
    `specs/tools/<tool>/<spec path>`, of the spec at that path."""

    def test_every_tool_spec_is_included(self) -> None:
        """A tool spec no prompt includes is dead text."""
        included = {path for text in _templates().values()
                    for path in _INCLUDE_RE.findall(text)}
        for path in sorted(_TOOLS.rglob("*.md")):
            rel = str(path.relative_to(deps.CHECKOUT))
            with self.subTest(spec=rel):
                self.assertIn(rel, included)

    def test_every_tool_include_resolves(self) -> None:
        """Deleting a tool spec ablates it silently, so a misspelled include is
        caught here rather than at run time."""
        for name, text in _templates().items():
            for path in _INCLUDE_RE.findall(text):
                if path.startswith(TOOLS_DIR + "/"):
                    with self.subTest(prompt=name, spec=path):
                        self.assertTrue((deps.CHECKOUT / path).is_file())

    def test_a_prompt_with_an_augmentation_carries_its_tool(self) -> None:
        for name, text in _templates().items():
            paths = _INCLUDE_RE.findall(text)
            for path in paths:
                if path.startswith(TOOLS_DIR + "/"):
                    tool = path.removeprefix(TOOLS_DIR + "/").split("/", 1)[0]
                    with self.subTest(prompt=name, spec=path):
                        self.assertIn(f"{TOOLS_DIR}/{tool}/{tool}.md", paths)


class IncludeTests(unittest.TestCase):
    """crustify's documents are spliced into the prompts that follow them;
    role headers name their sections when they augment them."""

    _DOCS = {
        "conventions": "specs/rust/conventions.md",
        "toolchain": "specs/rust/toolchain.md",
        "items/binding": "specs/rust/items/binding.md",
        "items/porting": "specs/rust/items/porting.md",
        "testing": "specs/verification/testing.md",
        "versioning": "specs/operations/versioning.md",
        "layout": "specs/operations/layout.md",
        "decomposition": "specs/planning/decomposition.md",
        "scheduling": "specs/planning/scheduling.md",
        "dependencies": "specs/planning/dependencies.md",
        "reviewing": "specs/verification/reviewing.md",
        "accounting": "specs/operations/accounting.md",
        "prompting": "specs/prompting.md",
        "workflows/setup": "specs/workflows/setup.md",
        "workflows/binding": "specs/workflows/binding.md",
        "workflows/porting": "specs/workflows/porting.md",
        "workflows/audit": "specs/workflows/audit.md",
    }
    _REF = re.compile(r"^## ([a-z/]+) › (.+?)(?:, for `[a-z]+`)?$", re.M)
    #: A numbered heading's number, which a reference leaves out.
    
    def _included(self, prompt: str) -> set[str]:
        if prompt.endswith("-assistant.md"):
            text = campaign_prompt(prompt.removesuffix("-assistant.md"))
        else:
            text = (_PKG_ROOT / "prompts" / prompt).read_text()
        return {name for name, path in self._DOCS.items()
                if f"<!-- INCLUDE {path} -->" in text}

    def test_each_prompt_includes_the_documents_it_follows(self) -> None:
        """The reviewer is told to ignore the conventions outside a
        Crustify-generated batch."""
        self.assertEqual(self._included("binder.md"),
                         {"conventions", "toolchain", "items/binding", "testing", "versioning",
                          "layout", "accounting"})
        self.assertEqual(self._included("translator.md"),
                         {"conventions", "toolchain", "items/binding", "items/porting", "testing",
                          "versioning", "layout", "accounting"})
        self.assertEqual(self._included("reviewer.md"),
                         {"conventions", "toolchain", "items/binding", "items/porting", "testing",
                          "versioning", "layout", "reviewing", "accounting"})
        self.assertEqual(self._included("planner.md"),
                         {"conventions", "decomposition", "scheduling", "dependencies",
                          "reviewing", "accounting"})
        shared = {"prompting", "workflows/setup", "versioning", "layout", "testing",
                  "reviewing", "accounting"}
        self.assertEqual(self._included("translate-assistant.md"),
                         shared | {"workflows/binding", "workflows/porting",
                                   "decomposition", "scheduling", "dependencies", "conventions", "toolchain", "items/binding",
                                   "items/porting"})
        self.assertEqual(self._included("audit-assistant.md"),
                         shared | {"workflows/audit"})

    def test_included_documents_are_plain_markdown(self) -> None:
        """Public documents: no frontmatter for an agent to see."""
        for name, path in self._DOCS.items():
            with self.subTest(doc=name):
                self.assertFalse(
                    (deps.CHECKOUT / path).read_text().startswith("---"))

    def test_an_included_document_survives_formatting(self) -> None:
        """The conventions carry literal braces (`mod ffi_export {{ … }}`), and the body
        is formatted after the include."""
        from crustify.agents.base import expand_includes
        body = expand_includes(
            "<!-- INCLUDE specs/rust/conventions.md -->")
        self.assertIn("mod ffi_export { use super::*;", body.format())


class AblationTests(unittest.TestCase):
    """A tool is ablated by deleting its header, and one of its uses by
    deleting that spec."""

    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parent

    def _agent(self, **kw) -> AssistAgent:
        return AssistAgent(self.repo, kind="translate", task=Path(__file__), **kw)

    def test_a_present_tool_is_carried(self) -> None:
        agent = self._agent()
        self.assertEqual(agent.prompt_capabilities(), ("wavefront", "ffimap", "ffibox"))
        self.assertIn("# wavefront › workflows/setup", agent.system_preamble())

    def test_deleting_a_tool_header_ablates_the_tool(self) -> None:
        real = Path.is_file
        header = _TOOLS / "wavefront/wavefront.md"
        with mock.patch.object(Path, "is_file",
                               lambda p: False if p == header else real(p)):
            agent = self._agent()
            self.assertNotIn("wavefront", agent.prompt_capabilities())
            self.assertNotIn("# wavefront › ", agent.system_preamble())

    def test_deleting_an_augmentation_ablates_that_use_only(self) -> None:
        real = Path.is_file
        aug = _TOOLS / "wavefront/workflows/setup.md"
        with mock.patch.object(Path, "is_file",
                               lambda p: False if p == aug else real(p)):
            pre = self._agent().system_preamble()
            self.assertNotIn("# wavefront › workflows/setup", pre)
            self.assertIn("# wavefront › operations/versioning", pre)

    def test_the_ablation_control_carries_no_tools(self) -> None:
        agent = self._agent(task_only=True)
        self.assertEqual(agent.prompt_capabilities(), ())
        self.assertEqual(agent.system_preamble(), "")


class PromptRenderTests(unittest.TestCase):
    """`run()` calls `prompt.format(**arguments)`, so a stage prompt holding
    literal braces must escape them. The orchestrator's does, since its body
    is the campaign playbook and that documents a directory tree."""

    def test_every_stage_prompt_survives_format(self) -> None:
        """Any placeholder resolves here; what is under test is that no
        unescaped literal brace makes `format` raise."""
        for path in [*(_PKG_ROOT / "prompts").glob("*.md"),
                     *(_PKG_ROOT / "prompts" / "assistant").glob("*.md")]:
            with self.subTest(prompt=path.name):
                path.read_text().format_map(collections.defaultdict(str))

    def test_every_campaign_kind_fills_the_assistant_prompt(self) -> None:
        """One shared prompt, one part per kind: a kind without its part, or a
        part the marker never reaches, fails at launch."""
        from crustify.cli import CAMPAIGNS
        for kind in sorted(set(CAMPAIGNS.values())):
            with self.subTest(kind=kind):
                text = campaign_prompt(kind)
                self.assertNotIn(CAMPAIGN_MARKER, text)
                self.assertIn(f"<!-- INCLUDE {TOOLS_DIR}/ffimap/ffimap.md -->", text)


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
    _BASE = {"workdir", "git_base", "batch_id", "module"}

    def _declared(self, body: str) -> set[str]:
        return set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", body))

    def _check(self, agent) -> None:
        declared, supplied = self._declared(agent._body()), set(agent._arguments())
        self.assertEqual(declared - supplied, set(), "placeholder with no argument")
        self.assertEqual(supplied - declared - self._BASE, set(),
                         "argument no placeholder names")

    def test_binder_arguments_match_its_placeholders(self) -> None:
        agent = BindAgent(
            self.repo, route="type",
            items=[{"name": "T", "defined_in": "a.h", "kind": "type",
                    "field_users": [], "home": "crustify/rust/x/src/a.rs"}],
            git_base="wave-0", log_stem="x")
        self._check(agent)

    def test_translator_arguments_match_its_placeholders(self) -> None:
        agent = TranslateAgent(
            self.repo, route="type",
            items=[{"name": "T", "defined_in": "a.h", "kind": "type",
                    "field_users": [], "home": "crustify/rust/x/src/a.rs"}],
            git_base="wave-0",
            log_stem="x")
        self._check(agent)

    def test_reviewer_arguments_match_its_placeholders(self) -> None:
        agent = ReviewAgent(
            self.repo, route="commits", commits=["3f2a9c1"],
            objectives=None, git_base="review-wave-0",
            log_stem="x")
        self._check(agent)

    def test_a_batch_agent_names_its_batch(self) -> None:
        agent = BindAgent(
            self.repo, route="type",
            items=[{"name": "T", "defined_in": "a.h", "kind": "type",
                    "field_users": [], "home": "crustify/rust/x/src/a.rs"}],
            git_base="crustify/waves/wave-3",
            log_stem="x")
        agent.placement = translate.Placement(3, 1, "lib", "src/core.c")
        arguments = agent._arguments()
        self.assertEqual(arguments["batch_id"], "wave-3/batch-1")
        self.assertEqual(arguments["module"], "lib/src/core.c")

    def test_planner_arguments_match_its_placeholders(self) -> None:
        self._check(PlanAgent(self.repo,
                              log_stem="x"))

    def test_orchestrator_arguments_match_its_placeholders(self) -> None:
        task = self.repo / "CRUSTIFY.md"
        task.write_text("- Answer: none")
        agent = AssistAgent(self.repo, kind="translate", task=task)
        self._check(agent)


class OrchestratorPromptTests(unittest.TestCase):
    """The orchestrator's whole prompt rides the system slot."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "crustify").mkdir()
        self.task = self.repo / "CRUSTIFY.md"
        self.task.write_text("1. **Q** (`id: source`)\n   - Answer: `{brace}`")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _agent(self, **kw):
        return AssistAgent(self.repo, kind="translate", task=self.task, **kw)

    def test_the_task_is_read_not_spliced(self) -> None:
        """The prompt says where the task lives; its answers stay in the file,
        so an edit made mid-campaign is what the next module runs under."""
        for kind in ("translate", "audit"):
            with self.subTest(kind=kind):
                pre = AssistAgent(
                    self.repo, kind=kind, task=self.task).system_preamble()
                self.assertNotIn("`{brace}`", pre)
                self.assertIn(f"{self.repo}/crustify/CRUSTIFY.md", pre)

    def test_the_user_turn_carries_no_instruction(self) -> None:
        """Everything the agent is told is in the system slot; neither backend
        accepts an empty positional, which is all the user turn is for."""
        agent = self._agent()
        self.assertLess(len(agent._prompt()), 100)
        self.assertGreater(len(agent.system_preamble()), 10_000)

    def test_an_empty_task_is_an_error(self) -> None:
        self.task.write_text("")
        with self.assertRaises(SystemExit):
            self._agent().system_preamble()

    def test_the_ablation_arm_contributes_nothing(self) -> None:
        agent = self._agent(task_only=True)
        self.assertEqual(agent.system_preamble(), "")
        self.assertEqual(agent.prompt_capabilities(), ())


class PromptCacheTests(unittest.TestCase):
    """A provider caches a prompt's prefix, so two batches of one role share
    everything before their inputs: the specs come first, and no per-run
    value appears before the Inputs section."""

    def test_two_batches_share_everything_before_their_inputs(self) -> None:
        import os
        def item(name):
            return [{"name": name, "defined_in": "a.h", "kind": "type",
                     "field_users": [], "home": "src/a.rs"}]
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for cls in (BindAgent, TranslateAgent):
                with self.subTest(role=cls.role):
                    one, two = (cls(Path(d), route="type", items=item(n),
                                    git_base=f"crustify/waves/wave-{i}",
                                    log_stem="x").system_preamble()
                                for i, (d, n) in enumerate(((a, "A"), (b, "B"))))
                    shared = len(os.path.commonprefix([one, two]))
                    self.assertGreaterEqual(shared, one.index("## Inputs"))


if __name__ == "__main__":
    unittest.main()
