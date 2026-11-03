"""One binder: binds the items of one orchestrator-written task."""
from __future__ import annotations

from crustify.agents.worklist import WorklistAgent


class BindAgent(WorklistAgent):
    """Bind one orchestrator-projected batch: keep its C implementation and
    put a safe Rust API in front of it."""

    name = "BindAgent"
    #: The agent its session record names.
    role = "binder"
    objective = "wrap"
    prompt = "binder.md"
