from __future__ import annotations

from pathlib import Path

import requests


class FileDownloader:
    def download(self, url: str, destination: Path, timeout_seconds: int = 30) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not url.startswith(("https://", "http://")):
            raise ValueError("Only HTTP or HTTPS downloads are supported.")
        with requests.get(url, timeout=timeout_seconds, stream=True) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        output.write(chunk)
        return destination
