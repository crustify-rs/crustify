"""Tunable knobs for the crustify pipeline."""


# ---------------------------------------------------------------------------
# Agent execution — model, backend, billing
# ---------------------------------------------------------------------------

MODEL_OVERRIDE: str | None = None
"""Set by the CLI ``--model`` flag. When non-None, every agent runs against
this model instead of its hard-coded per-agent default. None => each
agent's own default.

Named ``<provider>/<model>`` — see :mod:`crustify.models`."""

BILLING: str = "subscription"
"""How the provider CLI authenticates (set by the CLI ``--billing`` flag):

  - ``subscription`` -- the CLI's own logged-in account.
  - ``api`` -- an API key from the environment.

The distinction is not cosmetic: it selects a different auth path per CLI,
and for Claude it is not switchable by environment variable alone."""

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

LOG_TO_CONSOLE: bool = True
"""When ``False``, suppress live console output from agents."""
