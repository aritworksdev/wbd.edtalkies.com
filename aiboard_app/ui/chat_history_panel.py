from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem, QVBoxLayout

from aiboard_app.chat.chat_record import ChatRecord


class ChatHistoryPanel(QFrame):
    chat_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ChatHistoryPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)
        self._records: list[ChatRecord] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)

        self._list = QListWidget()
        self._list.setObjectName("ChatHistoryList")
        self._list.itemActivated.connect(self._emit_selected)
        self._list.itemClicked.connect(self._emit_selected)

        layout.addWidget(self._list, 1)

    def set_chats(self, records: list[ChatRecord]) -> None:
        self._records = records
        self._list.clear()
        for record in records:
            item = QListWidgetItem(self._item_text(record))
            item.setData(256, record.id)
            self._list.addItem(item)

    def _emit_selected(self, item: QListWidgetItem) -> None:
        chat_id = item.data(256)
        if chat_id:
            self.chat_selected.emit(str(chat_id))

    @staticmethod
    def _item_text(record: ChatRecord) -> str:
        created = record.created_at.strftime("%m/%d/%Y %I:%M %p")
        response = record.response_preview
        if response:
            return f"💬 {record.title}\n{created}\n{response}"
        return f"💬 {record.title}\n{created}"
