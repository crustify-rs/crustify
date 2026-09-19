"""Where crustify's dependencies live.

There is one rule: every out-of-tree dependency is a checkout under the
running interpreter's data prefix, at ``<prefix>/share/<name>/``, and every
executable is a console script in the same environment's ``bin/``. Both are
*derived* from the running interpreter rather than configured, because an agent
that is running crustify is by construction running it from somewhere, and
that somewhere is the answer.

This replaces ``crustify/cli-config.json``, whose ``deps`` and ``bins`` maps
existed only to spell those paths out per machine. The cost of the config was
not the file: it was that a machine-local, gitignored artifact had to be
correct before an agent could render its own prompt, and a stale entry
produced a silently different prompt rather than an error.

A ``CRUSTIFY_DEP_<NAME>`` environment variable overrides one dependency, for
a developer working against a local checkout that is not installed. Nothing
here ever walks the filesystem looking for a dependency: the path is either
derived or declared.
"""
from __future__ import annotations

import os
import shutil
import sysconfig
from pathlib import Path

#: The crustify checkout itself: ``src/crustify/`` → two levels up. crustify's
#: own skills, prompts and docs are read from here rather than from a share
#: path, because they ship with the code that renders them and cannot be
#: out of step with it.
CHECKOUT = Path(__file__).resolve().parent.parent.parent

#: Dependencies that are separate checkouts. The value is the share directory
#: name, which is also the environment-variable suffix.
_SHARED_DEPS = ("wavefront", "ffibox")


def bin_dir() -> Path:
    """The console-script directory of the environment crustify runs in.

    ``sysconfig``, not ``Path(sys.executable).parent``: in a venv the
    interpreter is a symlink, and resolving it lands in the base Python's
    ``bin/`` where none of the venv's entry points exist.
    """
    return Path(sysconfig.get_path("scripts"))


def share_dir() -> Path:
    """``<prefix>/share`` for the environment crustify runs in."""
    return Path(sysconfig.get_path("data")) / "share"


def dep_root(name: str) -> Path:
    """The checkout root for one dependency.

    ``crustify`` resolves to crustify's own checkout. Everything else is
    ``<prefix>/share/<name>``, overridable with ``CRUSTIFY_DEP_<NAME>``.
    """
    if name == "crustify":
        return CHECKOUT
    if name not in _SHARED_DEPS:
        raise SystemExit(f"unknown crustify dependency: {name}")
    override = os.environ.get(f"CRUSTIFY_DEP_{name.upper()}")
    return Path(override).resolve() if override else share_dir() / name


def resolve_bin(spec: str) -> str:
    """Absolute invocation for a skill's ``Bin path``.

    The spec is a logical executable optionally followed by subcommand words
    (``crustify audit``); only the first is a file to find. Falls back to
    ``PATH`` so a system-installed tool still resolves, and to the spec
    verbatim when neither locates it — a wrong path in a prompt is better
    diagnosed by the agent running it than by a crash at render time.
    """
    exe, _, rest = spec.partition(" ")
    candidate = bin_dir() / exe
    if not candidate.is_file():
        found = shutil.which(exe)
        if found is None:
            return spec
        candidate = Path(found)
    return f"{candidate} {rest}".rstrip()
