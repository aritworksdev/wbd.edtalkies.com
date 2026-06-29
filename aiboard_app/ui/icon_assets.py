from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon

LOGGER = logging.getLogger(__name__)

ICON_DIR = Path(__file__).resolve().parents[2] / "Assets" / "Icons"
LOGO_DIR = Path(__file__).resolve().parents[2] / "Assets" / "Logo"


class IconName:
    ASK_AI = "__ed_icon_ai2.png"
    CHATS = "__ed_icon_chats.png"
    CLOSE = "__ed_icon_close_window.png"
    COPY = "__ed_icon_copy.png"
    COLOR_WHEEL = "__ed_icon_color_wheel.png"
    CONSOLE = "__ed_icon_console_white.png"
    DELETE = "__ed_icon_delete.png"
    DOCX = "__db_icon_docx.png"
    EDIT = "__ed_icon_edit.png"
    ERASE = "__ed_icon_erase.png"
    EXCEL = "__db_icon_excel.png"
    KEYBOARD = "__ed_icon_keyboard_white.png"
    PLUS_OUTLINE = "__db_icon_plus_outline.png"
    PPTX = "__db_icon_pptx.png"
    REDO = "__ed_icon_redo_white.png"
    UNDO = "__ed_icon_undo_white.png"
    UPDATE = "__ed_icon_update_changes.png"
    UPLOAD = "__ed_icon_upload.png"


def icon_path(file_name: str) -> Path:
    return ICON_DIR / file_name


def logo_path(file_name: str) -> Path:
    return LOGO_DIR / file_name


def load_icon(file_name: str, fallback: str = IconName.EDIT) -> QIcon:
    path = icon_path(file_name)
    if path.exists():
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
        LOGGER.warning("Icon file exists but could not be loaded: %s", path)
    else:
        LOGGER.warning("Icon file is missing: %s", path)

    fallback_path = icon_path(fallback)
    if fallback_path.exists():
        return QIcon(str(fallback_path))
    return QIcon()
