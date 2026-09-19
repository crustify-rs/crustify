"""Which optional skills each agent role carries in its system prompt.

One tracked file, ``crustify/skills-config.json``, with one entry per role::

    {"orchestrator": ["wavefront", "audit"],
     "translator":   ["wavefront", "ffibox", "audit"]}

This is the prompt-composition knob, and it is separate from where the skill
files live (:mod:`crustify.deps`, derived from the environment) because the
two answer different questions and fail differently. A wrong path is a broken
run; a wrong selection is a *quietly different experiment*, which is why the
selection is tracked in git rather than kept in a machine-local config: the
commit a campaign lands carries the prompt composition it ran under, and an
ablation is a diff.

Being tracked also means an agent's worktree already holds it — ``git
worktree add`` checks it out from HEAD — so unlike the machine-local config
this replaces, nothing has to symlink it in.

Selection is descriptive, not an access boundary: dropping a capability
removes its metadata and role guidance from the system prompt. The tool, its
binary and its checkout stay exactly as reachable from the agent's shell.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Role keys the file may carry. A role absent from the file takes the
#: defaults its agent class declares, which is what an ordinary campaign
#: wants; the file exists to say something OTHER than "everything".
ROLES = ("orchestrator", "translator")


def load(path: Path) -> dict[str, list[str]]:
    """Parse and validate ``skills-config.json``. Absent file: no entries."""
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"{path}: {exc}") from None
    if not isinstance(doc, dict):
        raise SystemExit(f"{path}: must be a JSON object keyed by role")
    # `_`-prefixed keys are prose, the convention every crustify spec uses to
    # keep a file self-documenting in a format with no comment syntax.
    doc = {k: v for k, v in doc.items() if not k.startswith("_")}
    unknown = sorted(set(doc) - set(ROLES))
    if unknown:
        raise SystemExit(
            f"{path}: unknown role(s): {', '.join(unknown)}; "
            f"known: {', '.join(ROLES)}")
    for role, names in doc.items():
        if not isinstance(names, list) or not all(
                isinstance(n, str) and n for n in names):
            raise SystemExit(
                f"{path}: {role} must be a list of capability names")
    return doc


def selected(path: Path, role: str, known: tuple[str, ...],
             default: tuple[str, ...]) -> tuple[str, ...]:
    """The capability names one role carries, in prompt order.

    An absent entry takes ``default``. An empty list is a real answer — the
    ablation that carries no optional skill at all — and is distinct from
    absence, which is why this cannot be written as ``doc.get(role) or
    default``.
    """
    doc = load(path)
    if role not in doc:
        return default
    names = doc[role]
    unknown = sorted(set(names) - set(known))
    if unknown:
        raise SystemExit(
            f"{path}: unknown {role} capability: {', '.join(unknown)}; "
            f"known: {', '.join(known)}")
    # Preserve authored order in the prompt; collapse accidental repeats.
    return tuple(dict.fromkeys(names))
