"""How an agent's provider CLI runs: its backend, billing, model proxy and the
user's own arguments. Shared by both tools.

Crustify names no model. The backend is the CLI, ``claude`` or ``codex``, and
runs its own default model unless the user's arguments name another, in the
CLI's own syntax (``--model opus``, ``-m gpt-6-sol``). A model proxy is a
gateway that the CLI's requests go through with the proxy's key, such as
OpenRouter; it bills the run, so it decides the rates the run is priced at,
which the transcript alone cannot tell.

Raises ``ValueError``, not ``SystemExit``: a library says what is wrong and the
entry point decides whether that ends the process.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: The provider CLIs crustify drives.
BACKENDS = ("claude", "codex")

#: How a CLI authenticates: its own logged-in account, or an API key from
#: the environment.
BILLINGS = ("subscription", "api")

#: The service that bills a backend's runs without a proxy.
NATIVE = {"claude": "anthropic", "codex": "openai"}


@dataclass(frozen=True)
class Proxy:
    """A gateway the CLIs reach through their own endpoint settings."""

    #: The environment variable holding the proxy's key.
    key_env: str
    #: Its Anthropic-compatible endpoint, for claude.
    anthropic_url: str
    #: Its OpenAI-compatible (Responses) endpoint, for codex.
    openai_url: str
    #: Its display name.
    name: str


PROXIES = {
    "openrouter": Proxy(key_env="OPENROUTER_API_KEY",
                        anthropic_url="https://openrouter.ai/api",
                        openai_url="https://openrouter.ai/api/v1",
                        name="OpenRouter"),
}


@dataclass(frozen=True)
class Route:
    """One agent's run: which CLI, how it bills, through which proxy, and
    the arguments passed to the CLI after crustify's own."""

    backend: str
    billing: str = "subscription"
    model_proxy: str | None = None
    args: tuple[str, ...] = field(default_factory=tuple)

    @property
    def provider(self) -> str:
        """The service that bills the run, whose rates price it."""
        return self.model_proxy or NATIVE[self.backend]

    def record(self) -> dict:
        """The fields a session record keeps, to rerun or price it."""
        return {"backend": self.backend, "billing": self.billing,
                "model_proxy": self.model_proxy, "args": list(self.args)}


def _names_model(args: tuple[str, ...]) -> bool:
    return any(a in ("-m", "--model") or a.startswith(("-m=", "--model="))
               for a in args)


def route(backend: str, billing: str = "subscription",
          model_proxy: str | None = None, args=()) -> Route:
    """A checked :class:`Route`."""
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; expected one of: "
                         f"{', '.join(BACKENDS)}.")
    if billing not in BILLINGS:
        raise ValueError(f"unknown billing {billing!r}; expected one of: "
                         f"{', '.join(BILLINGS)}.")
    if model_proxy is not None and model_proxy not in PROXIES:
        raise ValueError(f"unknown model proxy {model_proxy!r}; expected one "
                         f"of: {', '.join(PROXIES)}.")
    if model_proxy is not None and billing != "api":
        raise ValueError(f"a model proxy bills by its own key: "
                         f"{model_proxy} needs --billing api.")
    args = tuple(args)
    if not all(isinstance(a, str) for a in args):
        raise ValueError("args must be strings")
    # Codex's default model is a bare OpenAI id, which a proxy does not know
    # by that name; Claude Code's defaults are mapped by the proxies it
    # supports.
    if backend == "codex" and model_proxy is not None and not _names_model(args):
        raise ValueError(f"codex through {model_proxy} needs its model named "
                         f"as the proxy knows it, e.g. -m openai/<model>.")
    return Route(backend, billing, model_proxy, args)


def from_model(model: str, billing: str) -> Route:
    """The route of an earlier ``<provider>/<model>`` name, as task.json and
    session records carried it."""
    provider, sep, model_id = (model or "").strip().partition("/")
    if not sep or not model_id:
        raise ValueError(f"model {model!r} must be named <provider>/<model>")
    if provider == "anthropic":
        return route("claude", billing, None, ("--model", model_id))
    if provider == "openai":
        return route("codex", billing, None, ("-m", model_id))
    if provider == "openrouter":
        backend = "claude" if model_id.startswith("anthropic/") else "codex"
        flag = "--model" if backend == "claude" else "-m"
        return route(backend, "api", "openrouter", (flag, model_id))
    raise ValueError(f"unknown provider {provider!r} in model {model!r}")
