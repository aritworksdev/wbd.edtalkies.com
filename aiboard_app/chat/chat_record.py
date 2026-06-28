from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aiboard_app.ai.response_parser import ParsedResponse, ResponseDocument


@dataclass(frozen=True)
class ChatRecord:
    id: str
    request_text: str
    response: ParsedResponse
    created_at: datetime
    session_id: str = ""

    @property
    def title(self) -> str:
        words = self.request_text.split()
        preview = " ".join(words[:8]) if words else self.response.title
        return preview[:80] + ("…" if len(preview) > 80 else "")

    @property
    def response_preview(self) -> str:
        source = self.response.text or self.response.html
        collapsed = " ".join(source.split())
        return collapsed[:100] + ("…" if len(collapsed) > 100 else "")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_text": self.request_text,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "response": {
                "title": self.response.title,
                "text": self.response.text,
                "html": self.response.html,
                "documents": [
                    {
                        "file_name": document.file_name,
                        "file_type": document.file_type,
                        "url": document.url,
                        "status": document.status,
                    }
                    for document in self.response.documents
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChatRecord:
        response_data = data.get("response")
        if not isinstance(response_data, dict):
            response_data = {}
        raw_documents = response_data.get("documents")
        documents: list[ResponseDocument] = []
        if isinstance(raw_documents, list):
            for document in raw_documents:
                if not isinstance(document, dict):
                    continue
                documents.append(
                    ResponseDocument(
                        file_name=str(document.get("file_name") or "document"),
                        file_type=str(document.get("file_type") or "unknown"),
                        url=str(document.get("url") or ""),
                        status=str(document.get("status") or "available"),
                    )
                )

        created_value = str(data.get("created_at") or "")
        try:
            created_at = datetime.fromisoformat(created_value)
        except ValueError:
            created_at = datetime.now()

        return cls(
            id=str(data.get("id") or ""),
            request_text=str(data.get("request_text") or ""),
            response=ParsedResponse(
                title=str(response_data.get("title") or "EdTalkies Response"),
                text=str(response_data.get("text") or ""),
                html=str(response_data.get("html") or ""),
                documents=documents,
            ),
            created_at=created_at,
            session_id=str(data.get("session_id") or ""),
        )
