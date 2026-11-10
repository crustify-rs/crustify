#!/usr/bin/env python3
"""The SubagentStop hook: copy a Crustify stage agent's transcript into Crustify's home,
`$CRUSTIFY_HOME/transcripts/<agent id>.jsonl`, the moment it ends, since the CLI prunes its
own copies. Codex runs it too, from this plugin's manifest, with the same event fields and
`CLAUDE_PLUGIN_ROOT` set. Standard library only."""
import json
import os
import shutil
import sys
from pathlib import Path

event = json.load(sys.stdin)
src = event.get("agent_transcript_path")
if src and Path(src).is_file():
    home = Path(os.environ.get("CRUSTIFY_HOME", Path.home() / ".crustify"))
    (home / "transcripts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, home / "transcripts" / f"{event.get('agent_id') or Path(src).stem}.jsonl")
