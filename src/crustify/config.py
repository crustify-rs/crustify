"""Tunable knobs for the crustify pipeline."""


# ---------------------------------------------------------------------------
# Agent execution — model, backend, billing
# ---------------------------------------------------------------------------

BACKEND: str = "claude"
"""The provider CLI every agent of this process runs on, ``claude`` or
``codex`` (set by ``--backend``, or a task's ``backend``). It runs its own
default model unless :data:`PROVIDER_ARGS` names another."""

BILLING: str = "subscription"
"""How the provider CLI authenticates (set by the CLI ``--billing`` flag):

  - ``subscription`` -- the CLI's own logged-in account.
  - ``api`` -- an API key from the environment.

The distinction is not cosmetic: it selects a different auth path per CLI,
and for Claude it is not switchable by environment variable alone."""

MODEL_PROXY: str | None = None
"""The gateway the CLI's requests go through, such as ``openrouter`` (set by
``--model-proxy``, or a task's ``model_proxy``); see
:mod:`crustify.core.models`."""

OVERRIDE_BASE_PROMPT: bool = False
"""Whether to replace the provider CLI's own base/system prompt with
crustify's (set by ``--override-base-prompt`` / ``--no-override-base-prompt``).

crustify's stage prompt is delivered as the user message either way; this
only controls whether the provider's own instructions survive underneath it.

Defaults to KEEPING the provider's prompt. Replacing it is markedly cheaper per
invocation, and that is why it was the default — but the v3 arm changed exactly
this and the wrappers improved, so the saving was buying worse output. The
provider's own instructions carry the tool-use and code-editing discipline the
stage prompt assumes rather than restates."""

PROVIDER_ARGS: list[str] = []
"""Arguments given after ``--`` on crustify's command line, passed through
unchanged to the provider CLI of every agent the command runs, after
crustify's own: ``crustify spawn-binder ... -- --effort high``."""

LOG_TO_CONSOLE: bool = True
"""When ``False``, suppress live console output from agents."""
