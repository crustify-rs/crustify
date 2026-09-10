"""Batch-local translation anchors.

The read-only ``crates`` command never writes Rust source. The translate
harness lays one batch's TODO anchors after forking its worktree so an agent
sees only the placeholders it owns.
"""

from __future__ import annotations

import re
from pathlib import Path


TODO = "// crustify:todo"


def _todo_anchor(item: str) -> str:
    return f"{TODO}: {item}"


def _anchor_re(name: str) -> "re.Pattern[str]":
    quoted = re.escape(name)
    return re.compile(
        rf"(?m)^\s*(?://+\s*(?:Replaces|Wraps):\s*{quoted}(?:\s|$)"
        rf"|{re.escape(TODO)}:\s*{quoted}\s*$)")


def _has_field_anchor(text: str, tag: str, field: str) -> bool:
    quoted = rf"{re.escape(tag)}\.{re.escape(field)}"
    return re.search(
        rf"(?m)^\s*(?://+\s*(?:Field|Wraps|Replaces):\s*{quoted}(?:\s|$)"
        rf"|{re.escape(TODO)}:\s*{quoted}\s*$)",
        text) is not None


def place_batch_anchors(
    layout,
    items: list[dict],
    *,
    emit: bool = True,
) -> tuple[int, list[str]]:
    """Insert a thin batch's anchors, using ``defined_in`` to select homes."""
    from crustify import crates

    doc = crates.load(layout)
    homes: dict[Path, list[dict]] = {}
    unanchored: list[str] = []
    for item in items:
        name = item["name"]
        hits = crates.lookup_all(doc, name, file=item.get("defined_in"))
        if not hits:
            unanchored.append(name)
            continue
        for hit in hits:
            path = crates.full_rs(layout, hit["crate_path"], hit["rs"])
            homes.setdefault(path, []).append(item)

    inserted = 0
    for rs_path, selected in homes.items():
        if not rs_path.exists():
            unanchored += [item["name"] for item in selected]
            continue
        contents = rs_path.read_text()
        additions: list[str] = []
        for selected_item in selected:
            name = selected_item["name"]
            wanted = [(name, None)] + [
                (f"{name}.{field}", field)
                for field in selected_item.get("field_anchors", ())
            ]
            for anchor, field in wanted:
                present = (
                    _has_field_anchor(contents, name, field)
                    if field else _anchor_re(anchor).search(contents)
                )
                if present or _todo_anchor(anchor) in additions:
                    continue
                if not emit:
                    unanchored.append(anchor)
                    continue
                additions += [_todo_anchor(anchor), ""]
        if additions:
            separator = ("" if contents.endswith("\n\n") else
                         "\n" if contents.endswith("\n") else "\n\n")
            rs_path.write_text(contents + separator + "\n".join(additions) + "\n")
            inserted += sum(1 for line in additions if line)

    return inserted, unanchored
