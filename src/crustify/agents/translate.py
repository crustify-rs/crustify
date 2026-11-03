"""One translator: ports the items of one orchestrator-written task."""
from __future__ import annotations

from crustify.agents.worklist import WorklistAgent

class TranslateAgent(WorklistAgent):
    """Port one orchestrator-projected batch to safe Rust."""

    name = "TranslateAgent"
    #: The agent its session record names.
    role = "translator"
    objective = "port"
    prompt = "translator.md"
