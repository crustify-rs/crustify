"""Where crustify keeps what belongs to its user rather than to a campaign."""
from __future__ import annotations

import os
from pathlib import Path


def crustify_home() -> Path:
    """Crustify's own home, shared by every campaign of this user:
    ``$CRUSTIFY_HOME``, or ``~/.crustify``."""
    return Path(os.environ.get("CRUSTIFY_HOME") or Path.home() / ".crustify")
