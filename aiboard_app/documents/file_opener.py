from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class FileOpener:
    def open_file(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
