from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from aiboard_app.documents.file_downloader import FileDownloader
from aiboard_app.documents.file_opener import FileOpener
from aiboard_app.documents.document_text_extractor import DocumentTextExtractor
from aiboard_app.recognition.ocr_result import OcrResult
from aiboard_app.recognition.ocr_service import OcrService


class DocumentManager:
    def __init__(
        self,
        export_dir: Path,
        timeout_seconds: int = 30,
        ocr_service: OcrService | None = None,
    ) -> None:
        self._download_dir = export_dir / "downloads"
        self._timeout_seconds = timeout_seconds
        self._downloader = FileDownloader()
        self._opener = FileOpener()
        self._extractor = DocumentTextExtractor(ocr_service) if ocr_service else None

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

    def extract_text(self, path: Path) -> OcrResult:
        if self._extractor is None:
            raise RuntimeError("Document OCR service is not configured.")
        return self._extractor.extract(path)
