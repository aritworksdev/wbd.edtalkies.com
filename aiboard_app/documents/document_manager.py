from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from aiboard_app.documents.file_downloader import FileDownloader
from aiboard_app.documents.file_opener import FileOpener

class DocumentManager:
    def __init__(self, export_dir: Path, timeout_seconds: int = 30) -> None:
        self._download_dir = export_dir / "downloads"
        self._timeout_seconds = timeout_seconds
        self._downloader = FileDownloader()
        self._opener = FileOpener()

    def open_url(self, url: str) -> None:
        path = self.download(url)
        self._opener.open_file(path)

    def open_file(self, path: object) -> None:
        if not isinstance(path, Path):
            raise TypeError("Downloaded document path is invalid.")
        self._opener.open_file(path)

    def download(self, url: str, file_name: str | None = None) -> Path:
        parsed = urlparse(url)
        inferred_name = Path(unquote(parsed.path)).name or "download"
        safe_name = Path(file_name or inferred_name).name
        return self._downloader.download(
            url,
            self._download_dir / safe_name,
            self._timeout_seconds,
        )
