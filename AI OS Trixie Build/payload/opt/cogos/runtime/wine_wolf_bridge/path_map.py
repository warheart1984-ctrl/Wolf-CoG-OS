"""Map Wine/Windows paths to governed Linux paths."""

from __future__ import annotations

import os
from pathlib import Path


def wine_to_linux(path: str, *, user: str | None = None) -> str:
    p = path.replace("\\", "/")
    user = user or os.environ.get("USER", "operator")
    home = str(Path.home())
    lower = p.lower()
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].upper()
        rest = p[2:].lstrip("/\\")
        if drive == "C":
            if rest.lower().startswith("users/"):
                parts = rest.split("/", 2)
                if len(parts) >= 3:
                    return str(Path(home) / parts[2])
                if len(parts) == 2:
                    return home
            if rest.lower().startswith("windows"):
                return "/usr/share/wine/windows"
            return str(Path(home) / rest) if rest else home
        return str(Path(home) / f".wine/drives/{drive}" / rest)
    if p.startswith("//") or p.startswith("\\\\"):
        return p
    if not p.startswith("/"):
        return str(Path(home) / p)
    return p
