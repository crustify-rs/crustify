from __future__ import annotations

import hashlib
import re as _re
from dataclasses import dataclass
from pathlib import Path

from crustify import deps
from crustify.agentlog import AgentLog, open_agent_log
from crustify.layout import Layout

# Package root — used to locate prompts/.
_PKG_ROOT = Path(__file__).parent.parent

#: The user turn for an agent whose body rides the system slot. Both backends
#: pass it as the provider CLI's positional task and neither accepts an empty
#: one, so such an agent still needs a sentence -- but only a sentence:
#: everything it is actually told is in the system slot.
KICKOFF = "Start the work described by your system prompt."


#: Where a stage prompt takes its task's additional instructions: replaced by
#: the instructions file's text, or by nothing when the task gives none.
INSTRUCTIONS_MARKER = "<!-- INSTRUCTIONS -->"

#: `<!-- INCLUDE specs/rust/items/binding.md -->`: a crustify document,
#: by its path in the checkout, spliced whole into a stage prompt.
_INCLUDE_RE = _re.compile(r"<!-- INCLUDE ([^ ]+) -->")

#: The specs of the tools an agent reaches for: `specs/tools/<tool>/<tool>.md`,
#: the tool's header, and `specs/tools/<tool>/<spec path>`, how the tool serves
#: the spec at that path. A prompt includes each it needs, as it includes any spec.
TOOLS_DIR = "specs/tools"

def _tool_of(path: str) -> str | None:
    """The tool a spec path belongs to, or None for a spec of no tool."""
    if not path.startswith(TOOLS_DIR + "/"):
        return None
    return path[len(TOOLS_DIR) + 1:].split("/", 1)[0]


def _header(tool: str) -> str:
    """A tool's header, by its path in the checkout."""
    return f"{TOOLS_DIR}/{tool}/{tool}.md"


def tool_available(tool: str) -> bool:
    """Whether a tool's specs are spliced into the prompts that include them:
    its header is on disk. The tool itself is on the agent's ``PATH``, or in
    its build, by the time the agent runs.

    Presence is the whole selection mechanism, so a tool is ablated by
    deleting its header, and one of its uses by deleting that spec."""
    return (deps.CHECKOUT / _header(tool)).is_file()


def included_tools(template: str) -> tuple[str, ...]:
    """The available tools whose headers a prompt template includes, in order."""
    tools = []
    for path in _INCLUDE_RE.findall(template):
        tool = _tool_of(path)
        if (tool and path == _header(tool) and tool not in tools
                and tool_available(tool)):
            tools.append(tool)
    return tuple(tools)


def expand_includes(text: str) -> str:
    """Splice every included document into a stage prompt template.

    The documents are the specs under ``specs/``: public, human-readable
    descriptions that an agent follows throughout, so the prompt hands them
    over whole rather than naming a file the agent may skip reading. Braces
    are escaped, because the template is formatted with the agent's arguments
    afterwards and the documents are not templates.

    A missing spec is an error, not an ablation, but for a tool's: a tool spec
    that is missing, or whose tool is not available, splices nothing, which is
    how a tool or one of its uses is ablated."""
    def splice(m: _re.Match) -> str:
        rel = m.group(1)
        path = deps.CHECKOUT / rel
        tool = _tool_of(rel)
        if tool is not None:
            if not (tool_available(tool) and path.is_file()):
                return ""
        elif not path.is_file():
            raise SystemExit(f"included document does not exist: {path}")
        return path.read_text().strip().replace("{", "{{").replace("}", "}}")
    return _INCLUDE_RE.sub(splice, text)


class CrustifyAgent:
    """One pipeline stage, driven by a provider-CLI backend.

    Each agent runs against a *workdir*: the checkout it reads and writes.
    For an isolated wave agent that is its own worktree, which is why every
    path the prompt hands it resolves there rather than in the main
    repo.

    A batch agent writes its log and usage record into the explicit
    ``artifact_dir`` it is given; an agent without one logs under
    ``crustify/logs``.
    """

    name: str         # subclasses set this
    model: str        # subclasses set this
    #: The agent a session record names: binder, translator, reviewer, planner
    #: or assistant. Subclasses set this.
    role: str = "agent"
    stage: str        # label recorded in the usage record + log filename
    #: Where this agent's stage prompt goes. False puts it in the user turn,
    #: which is right when it carries per-agent data: a wave's translators
    #: would otherwise each have a different system prefix to cache. True puts
    #: the whole body in the system slot, out of reach of compaction, and
    #: leaves the user turn a kickoff.
    prompt_in_system_slot: bool = False
    #: Hand the terminal to the provider CLI's own interface rather than run
    #: it headless. Only an agent a person supervises live sets it: a
    #: headless run cannot stop to ask a question and wait for the answer.
    interactive: bool = False
    # Set per-instance (not class) when an agent is one of many running
    # in parallel — disambiguates log filenames so concurrent agents
    # don't clobber each other's logs. None on instances that don't
    # need disambiguation.
    stage_suffix: str | None = None
    #: The task's additional instructions (a
    #: :class:`crustify.translate.Instructions`), or None. Set per instance
    #: by the harness that read the task; the stage prompt's
    #: ``<!-- INSTRUCTIONS -->`` marker takes their text.
    instructions = None
    #: Where a batch's task sits in the schedule (a
    #: :class:`crustify.translate.Placement`), set per instance by the harness
    #: that read the task; None for an agent of no batch.
    placement = None

    def __init__(
        self,
        workdir: Path,
        *,
        git_base: str = "",
        artifact_dir: Path | None = None,
        log_stem: str | None = None,
    ) -> None:
        # An isolated-wave agent is constructed with its WORKTREE, so every
        # `crustify <command> <workdir> …` the prompt runs — and every artifact path
        # (rust/, logs) — resolves to the worktree, not the main checkout.
        # Without it, parallel agents' Rust-tree writes and commits leak into
        # the shared main checkout.
        self.layout = Layout(workdir)
        self.workdir = self.layout.workdir
        self.git_base = git_base
        # Where this agent's artifacts land. For a batch that is its own
        # directory under the wave: the log and usage record, and whatever
        # else the agent is told to write there.
        self.artifact_dir = artifact_dir
        self.log_stem = log_stem

    def run(self) -> None:
        prompt = self._prompt()
        system_preamble = self.system_preamble()
        arguments = self._arguments()
        rendered_prompt = prompt.format(**arguments)
        from crustify import config as _cfg
        from crustify.agents.backends import get_backend
        from crustify.core.models import resolve as _resolve_model

        # The model selects the backend: a Claude model can only be driven
        # by the claude CLI, an OpenAI one only by codex.
        model = _cfg.MODEL_OVERRIDE or self.model
        try:
            route = _resolve_model(model)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        backend = get_backend(route.backend)
        cli = "claude" if route.backend == "claude_cli" else "codex"
        provider_home = self.layout.providers(cli)
        #: The session to resume, when the agent continues one.
        resume = getattr(self, "resume", None)

        with self._make_log() as log:
            caps = ", ".join(self.prompt_capabilities()) or "none"
            prompt_hash = hashlib.sha256(
                (system_preamble + "\0" + rendered_prompt).encode()
            ).hexdigest()
            log.line(f"[crustify] prompt capabilities: {caps}")
            log.line(f"[crustify] prompt hash: {prompt_hash}")
            backend.run(
                name=self.name,
                route=route,
                prompt=rendered_prompt,
                system_preamble=system_preamble,
                work_dir=str(self.workdir),
                log=log,
                billing=_cfg.BILLING,
                override_base_prompt=_cfg.OVERRIDE_BASE_PROMPT,
                provider_home=provider_home,
                interactive=self.interactive,
                **({"resume": resume} if resume else {}),
                # A session id chosen before the run, where the CLI takes one.
                **({"session_id": self.session_id}
                   if getattr(self, "session_id", None) else {}),
            )

    def _log_stem(self) -> str:
        """Filename stem for this agent's logs, unique within its directory.

        ``stage_suffix`` disambiguates concurrent agents of the same stage so
        they never clobber each other's files.
        """
        stem = self.stage.replace("/", "_").replace(" ", "_")
        if self.stage_suffix:
            safe_suffix = (
                self.stage_suffix
                .replace("/", "_")
                .replace(" ", "_")
                .replace(".", "_")
            )
            stem = f"{stem}__{safe_suffix}"
        return stem

    def _make_log(self) -> AgentLog:
        """Open this agent's output sinks (see :mod:`crustify.agentlog`).

        A batch harness injects its explicit output directory and fixed log
        stem. An agent without one, the orchestrator, logs under
        ``crustify/logs``.
        """
        return open_agent_log(
            self.artifact_dir or self.layout.root / "logs",
            self.log_stem or self._log_stem(),
            agent=self.role,
            **self._index(),
        )

    def _index(self) -> dict:
        """Where this agent's session is indexed, and with which facts:
        nowhere, but for the assistant."""
        return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prompt(self) -> str:
        """What the backend puts in the user turn.

        A kickoff sentence when this agent's body rides the system slot --
        both provider CLIs pass this as their positional task and neither
        accepts an empty one, so there has to be something, but only that.
        """
        return KICKOFF if self.prompt_in_system_slot else self._body()

    def _template(self) -> str:
        """This stage's prompt template, its specs not yet included."""
        raise NotImplementedError

    def _body(self) -> str:
        """This stage's prompt, its specs included, before argument
        substitution: no substitution beyond the caller's
        `.format(**arguments)`."""
        return expand_includes(self._template())

    def _arguments(self) -> dict:
        # `workdir` is the full path every `crustify <command> <workdir> …` invocation
        # in a prompt needs. `git_base` is the unchecked-out wave
        # integration branch supplied by the orchestrator. Supplied to every
        # agent: `str.format` ignores a key the template does not reference, and
        # a template referencing a key nobody supplies dies before the request.
        # Subclasses extend (super()._arguments()).
        # `batch_id` and `module` place a batch's agent in the schedule.
        placement = self.placement
        return {
            "workdir": str(self.workdir),
            "git_base": self.git_base,
            "batch_id": placement.batch_id if placement else "",
            "module": placement.module_label if placement else "",
        }

    def prompt_capabilities(self) -> tuple[str, ...]:
        """The tools this prompt ended up carrying: those whose headers it
        includes and that are available.

        Logged per run, so the transcript records what the agent was told
        without anyone having to reconstruct which files were on disk at the
        time. Descriptive, not an access-control boundary: a tool that is
        absent from the prompt stays reachable through the ordinary shell.
        """
        return included_tools(self._template())

    def system_preamble(self) -> str:
        """What the backend puts in its system slot, above the stage prompt.

        An agent that sets `prompt_in_system_slot` puts its whole body here,
        with the specs and the tool specs it includes: the system prompt is
        not part of ``messages``, so nothing a long run does can summarize the
        procedure away. That trades the shared prefix away when the body
        carries per-agent data: a wave's translators then each write their own
        preamble instead of N-1 of them reading one. The trade is deliberate --
        the shared prefix only ever saved those N-1 first-turn writes, because
        longest-prefix matching sends every later turn to the agent's own
        chain, while compaction reaching the procedure costs the run itself.
        """
        if not self.prompt_in_system_slot:
            return ""
        return self._fill_instructions(self._body().format(**self._arguments()))

    def _fill_instructions(self, body: str) -> str:
        """``body`` with its instructions marker replaced by the task's
        additional instructions, or by nothing when it has none.

        Replaced after formatting, so braces in the instructions are text.
        Every word around them is the stage prompt's own: the marker sits in
        a section that states their precedence, and this adds nothing to it.
        A task with instructions for a prompt without the marker fails rather
        than lose them."""
        if self.instructions is None:
            return body.replace(INSTRUCTIONS_MARKER, "")
        if body.count(INSTRUCTIONS_MARKER) != 1:
            raise SystemExit(
                f"{self.role}: the prompt has no single {INSTRUCTIONS_MARKER} "
                "marker to take the task's instructions")
        return body.replace(INSTRUCTIONS_MARKER, self.instructions.text)
