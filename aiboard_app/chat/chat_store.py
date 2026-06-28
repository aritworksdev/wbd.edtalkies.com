from __future__ import annotations

import json
from pathlib import Path

from aiboard_app.chat.chat_record import ChatRecord


class ChatStore:
    def __init__(self, export_dir: Path) -> None:
        self._path = export_dir / "chats" / "chats.json"

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[ChatRecord]:
        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as input_file:
                raw = json.load(input_file)
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        records = [ChatRecord.from_dict(item) for item in raw if isinstance(item, dict)]
        return self._newest_first(records)

    def save_chat(self, chat: ChatRecord) -> list[ChatRecord]:
        records = [record for record in self.load() if record.id != chat.id]
        records.append(chat)
        records = self._newest_first(records)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as output_file:
            json.dump([record.to_dict() for record in records], output_file, indent=2)
        return records

    @staticmethod
    def _newest_first(records: list[ChatRecord]) -> list[ChatRecord]:
        return sorted(records, key=lambda record: record.created_at, reverse=True)
