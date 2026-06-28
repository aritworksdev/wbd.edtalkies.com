from __future__ import annotations

from datetime import datetime, timedelta
import zipfile

from aiboard_app.ai.response_parser import ParsedResponse
from aiboard_app.chat.chat_exporter import ChatExporter
from aiboard_app.chat.chat_record import ChatRecord
from aiboard_app.chat.chat_store import ChatStore


def _chat(chat_id: str, created_at: datetime) -> ChatRecord:
    return ChatRecord(
        id=chat_id,
        request_text="What is photosynthesis?",
        response=ParsedResponse(
            title="Photosynthesis",
            text="Photosynthesis is how plants make food.",
            html="<p>Photosynthesis is how plants make food.</p>",
        ),
        created_at=created_at,
        session_id="session-1",
    )


def test_chat_store_persists_newest_first(tmp_path) -> None:
    store = ChatStore(tmp_path)
    older = _chat("older", datetime.now() - timedelta(days=1))
    newer = _chat("newer", datetime.now())

    store.save_chat(older)
    records = store.save_chat(newer)

    assert [record.id for record in records] == ["newer", "older"]
    reloaded = store.load()
    assert [record.id for record in reloaded] == ["newer", "older"]
    assert reloaded[0].request_text == "What is photosynthesis?"


def test_chat_exporter_writes_txt_docx_and_pdf(tmp_path) -> None:
    chat = _chat("chat-1", datetime(2026, 6, 28, 10, 30, 0))
    exporter = ChatExporter(tmp_path)

    txt_path = exporter.export(chat, "txt")
    docx_path = exporter.export(chat, "docx")
    pdf_path = exporter.export(chat, "pdf")
    xlsx_path = exporter.export(chat, "xlsx")
    pptx_path = exporter.export(chat, "pptx")

    text = txt_path.read_text(encoding="utf-8")
    assert "What is photosynthesis?" in text
    assert "Photosynthesis is how plants make food." in text
    assert "2026-06-28 10:30:00" in text
    assert docx_path.exists()
    assert pdf_path.exists()
    assert xlsx_path.exists()
    assert pptx_path.exists()
    assert docx_path.name == "AiBoard_Chat_20260628_103000.docx"
    assert pdf_path.name == "AiBoard_Chat_20260628_103000.pdf"
    assert xlsx_path.name == "AiBoard_Chat_20260628_103000.xlsx"
    assert pptx_path.name == "AiBoard_Chat_20260628_103000.pptx"
    with zipfile.ZipFile(xlsx_path) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "What is photosynthesis?" in sheet
    with zipfile.ZipFile(pptx_path) as archive:
        slide = archive.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "Photosynthesis is how plants make food." in slide
