"""Crustify's assistant, the campaign's user-facing agent, run as an ordinary crustify agent.

It used to be started by shell: the container cat'd a prompt, appended a task
and some context, and exec'd `claude` or `codex` directly. That path had no
system slot at all -- every word the longest-lived agent in a campaign was
given sat in `messages`, where compaction can paraphrase it away -- and it
left no session record, so the supervision cost of every campaign to date
is unrecorded. Routing it through the same backend as every other agent fixes
both, and deletes the second way of starting a CLI that lived in that
shell.
"""
from __future__ import annotations

from pathlib import Path

from crustify.agents.base import (
    CrustifyAgent, _PKG_ROOT, expand_includes,
)

#: Where the assistant's one prompt, `prompts/assistant.md`, takes its campaign
#: kind's part: replaced by `prompts/assistant/<kind>.md`, what the assistant
#: owns in that kind of campaign and the documents only that kind includes.
CAMPAIGN_MARKER = "<!-- CAMPAIGN -->"
CAMPAIGN_SPECS_MARKER = "<!-- CAMPAIGN SPECS -->"
CAMPAIGN_GUIDE_MARKER = "<!-- CAMPAIGN GUIDE -->"
SPECS_END = "<!-- CAMPAIGN SPECS END -->"
GUIDE_START = "<!-- CAMPAIGN GUIDE START -->"


def campaign_prompt(kind: str) -> str:
    """The assistant's prompt template for one campaign kind, its documents not
    yet included: the shared prompt with the kind's part in its markers.

    A kind's file holds three parts, in order: the specs only that kind
    includes, up to `<!-- CAMPAIGN SPECS END -->`, which join the shared Specs
    section; what the assistant owns and does in that kind, up to
    `<!-- CAMPAIGN GUIDE START -->`, which fills the Campaign section; and how
    those specs apply, which closes the shared How the specs apply section."""
    shared = (_PKG_ROOT / "prompts" / "assistant.md").read_text()
    for marker in (CAMPAIGN_SPECS_MARKER, CAMPAIGN_MARKER, CAMPAIGN_GUIDE_MARKER):
        if shared.count(marker) != 1:
            raise SystemExit(f"assistant.md must hold one {marker} marker")
    part = (_PKG_ROOT / "prompts" / "assistant" / f"{kind}.md").read_text()
    specs, sep1, rest = part.partition(SPECS_END)
    campaign, sep2, guide = rest.partition(GUIDE_START)
    if not (sep1 and sep2):
        raise SystemExit(f"assistant/{kind}.md must hold {SPECS_END} and {GUIDE_START}")
    return (shared.replace(CAMPAIGN_SPECS_MARKER, specs.strip())
            .replace(CAMPAIGN_MARKER, campaign.strip())
            .replace(CAMPAIGN_GUIDE_MARKER, guide.strip()))


#: The first turn of a session started with `--start`: the user's instruction
#: to run the campaign as its settings configure it. Without `--start` there
#: is no first turn, and the user types it.
#: ``checkout`` left out: the session's workdir is its checkout.
_WORKDIR = object()

START = ("Start the campaign: run your workflow end to end, as "
         "crustify/CRUSTIFY.md configures it.")


class AssistAgent(CrustifyAgent):
    """Crustify's assistant for one `translate` or `audit` campaign: it talks to
    the user and orchestrates the campaign's sub-agents."""

    name = "assistant"
    #: The agent its session record names.
    role = "assistant"
    stage = "assist"
    prompt_in_system_slot = True

    def __init__(self, workdir: Path, *, kind: str, task: Path,
                 task_only: bool = False,
                 interactive: bool = False, start: bool = False,
                 resume: str | None = None, checkout=_WORKDIR,
                 session_id: str | None = None, **kwargs) -> None:
        self.kind = kind
        self.task = Path(task)
        self.task_only = task_only
        #: The orchestrator presents a brief and waits at approval gates, so
        #: with a person at the terminal it runs in the CLI's own interface.
        self.interactive = interactive
        #: Whether the session opens by starting the campaign. Without it the
        #: assistant opens idle, with its workflow in the system slot, and
        #: waits for the user's instructions.
        self.start = start
        #: The session id this run resumes, if any. Its system prompt is
        #: rendered again, as the workflow stands now: neither CLI keeps it
        #: with the conversation.
        self.resume = resume
        #: The campaign's repository, or None while it is not established:
        #: ``workdir`` is only where the CLI runs, the directory the session
        #: started in, which a resume returns to.
        if checkout is _WORKDIR:
            checkout = workdir
        self.checkout = Path(checkout).resolve() if checkout is not None else None
        #: The id a new session takes, which names its directory in
        #: crustify's home before the CLI starts.
        self.session_id = session_id
        self.stage_suffix = kind
        super().__init__(workdir, **kwargs)

    def _arguments(self) -> dict:
        # Before the repository is established, the prompt names it `<repo>`,
        # which its Repository section describes.
        return {**super()._arguments(),
                "workdir": str(self.checkout) if self.checkout else "<repo>",
                "settings": str(self.task),
                "cwd": str(self.workdir),
                "session_dir": str(self.artifact_dir or self.layout.root / "logs")}

    def _index(self) -> dict:
        # The session's directory in crustify's home holds its index entry,
        # so `crustify --resume` finds it from any directory, and the
        # directory to run the CLI in: its transcript is filed by that.
        if self.artifact_dir is None:
            return {}
        return {"index_path": self.artifact_dir / "index.json",
                "index_facts": {
                    "cwd": str(self.workdir),
                    "workdir": str(self.checkout) if self.checkout else None,
                    "dir": str(self.artifact_dir)}}

    def _task_text(self) -> str:
        text = self.task.read_text().strip()
        if not text:
            raise SystemExit(f"campaign settings file is empty: {self.task}")
        return text

    def prompt_capabilities(self) -> tuple[str, ...]:
        # `--task-only` is the control arm: the harness contributes nothing,
        # so it contributes no tool either.
        return () if self.task_only else super().prompt_capabilities()

    def _body(self) -> str:
        """The stage prompt. The campaign settings are not in it: the prompt says
        where the task lives, and the orchestrator reads it from there, so an
        edit made mid-campaign is what the next module runs under."""
        self._task_text()
        return super()._body()

    def _template(self) -> str:
        return campaign_prompt(self.kind)

    def _prompt(self) -> str:
        if self.task_only:
            # The ablation control: the harness contributes nothing, so the
            # task file is the whole prompt and the system slot stays empty.
            return self._task_text().replace("{", "{{").replace("}", "}}")
        return START if self.start else ""

    def system_preamble(self) -> str:
        """Empty for the ablation arm, the base composition otherwise.

        The base puts this agent's whole body in the system slot, because
        `prompt_in_system_slot` is set: the orchestrator is one agent running
        for hundreds of turns, and what compaction would paraphrase away is
        its own procedure. The campaign's decisions are not here: they live
        in the task file, which the procedure tells it to reread.
        """
        return "" if self.task_only else super().system_preamble()
