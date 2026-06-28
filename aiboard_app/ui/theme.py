from __future__ import annotations


class EdTalkiesTheme:
    FONT_DISPLAY = '"Poppins", "Segoe UI", Arial, sans-serif'
    FONT_BODY = '"Quicksand", "Segoe UI", Arial, sans-serif'
    FONT_MONO = 'Consolas, "Courier New", monospace'

    BLACK = "#000000"
    DEEP_NAVY = "#05051f"
    GLASS_NAVY = "#0b1230"
    PANEL = "#111827"
    PANEL_SOFT = "#17212f"
    PANEL_LINE = "rgba(255, 255, 255, 0.18)"
    TEXT = "#ffffff"
    TEXT_MUTED = "#d1d5db"
    TEXT_SOFT = "#aab2c0"
    PURPLE = "#9370db"
    BLUE = "#1e90ff"
    CYAN = "#00bfff"
    GREEN = "#10a37f"
    GREEN_HOVER = "#0e8e6d"
    WARNING = "#f59e0b"
    RESPONSE_BG = "#f8fafc"
    RESPONSE_TEXT = "#111827"

    @classmethod
    def app_stylesheet(cls) -> str:
        return f"""
        QWidget {{
            font-family: {cls.FONT_BODY};
            color: {cls.TEXT};
        }}
        #AppRoot, #AiBoardMainWindow {{
            background: {cls.BLACK};
        }}
        #AppHeader, #AppFooter {{
            background: rgba(0, 0, 80, 0.35);
            border: 0;
        }}
        #AppHeader {{
            border-bottom: 1px solid {cls.PANEL_LINE};
        }}
        #AppFooter {{
            border-top: 1px solid {cls.PANEL_LINE};
        }}
        #AppHeaderTitle {{
            color: {cls.TEXT};
            font-family: {cls.FONT_DISPLAY};
            font-size: 24px;
            font-weight: 800;
        }}
        #AppHeaderLogo {{
            line-height: 0.6;
            border-right-style: solid;
            border-right-width: 0px;
            border-right-color: cornflowerblue;
            font-family: {cls.FONT_DISPLAY};
            font-size: 36px;
            font-weight: 1000;
            color: {cls.TEXT};
            padding: 0px;
            margin: 0px;
            text-decoration: underline;
            text-decoration-thickness: 1px;
        }}
        #AppFooterText {{
            color: {cls.TEXT_MUTED};
            font-family: {cls.FONT_BODY};
            font-size: 13px;
            font-weight: 600;
        }}
        #WhiteboardToolbar {{
            background: rgba(0, 0, 80, 0.28);
            border-bottom: 1px solid {cls.PANEL_LINE};
        }}
        #WhiteboardToolbar QPushButton {{
            background: transparent;
            color: {cls.TEXT};
            border: 0;
            border-radius: 10px;
            padding: 4px;
            font-family: {cls.FONT_BODY};
            font-size: 15px;
            font-weight: 700;
        }}
        #WhiteboardToolbar QPushButton:hover {{
            background: rgba(255, 255, 255, 0.10);
        }}
        #WhiteboardToolbar QPushButton:focus {{
            background: rgba(255, 255, 255, 0.08);
        }}
        #WhiteboardToolbar QPushButton:checked {{
            background: rgba(147, 112, 219, 0.22);
        }}
        #WhiteboardToolbar QSlider::groove:horizontal {{
            height: 5px;
            background: rgba(255, 255, 255, 0.24);
            border-radius: 2px;
        }}
        #WhiteboardToolbar QSlider::handle:horizontal {{
            background: {cls.PURPLE};
            width: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }}
        #ResponsePanel {{
            background: {cls.RESPONSE_BG};
            border-left: 1px solid #dbe3ef;
            color: {cls.RESPONSE_TEXT};
        }}
        #ResponsePanel QPushButton {{
            background: transparent;
            color: {cls.TEXT};
            border: 0;
            border-radius: 10px;
            padding: 4px;
            font-family: {cls.FONT_BODY};
            font-weight: 700;
        }}
        #ResponsePanel QPushButton:hover {{
            background: rgba(16, 163, 127, 0.12);
        }}
        #ResponsePanel QPushButton:focus {{
            background: rgba(30, 144, 255, 0.12);
        }}
        #ResponseTitle {{
            font-family: {cls.FONT_DISPLAY};
            font-size: 22px;
            font-weight: 800;
            color: {cls.RESPONSE_TEXT};
        }}
        #ResponseExportLabel {{
            color: {cls.RESPONSE_TEXT};
            font-family: {cls.FONT_BODY};
            font-weight: 700;
        }}
        #ConsoleLogPanel {{
            background: {cls.GLASS_NAVY};
            border-left: 1px solid {cls.PANEL_LINE};
        }}
        #ConsoleLogTitle {{
            color: {cls.TEXT};
            font-family: {cls.FONT_DISPLAY};
            font-size: 18px;
            font-weight: 800;
        }}
        #ConsoleLogOutput {{
            background: rgba(0, 0, 0, 0.72);
            color: {cls.TEXT_MUTED};
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 10px;
            padding: 8px;
            font-family: {cls.FONT_MONO};
            font-size: 12px;
        }}
        #ChatHistoryPanel {{
            background: {cls.GLASS_NAVY};
            border-left: 1px solid {cls.PANEL_LINE};
        }}
        #ChatHistoryTitle {{
            color: {cls.TEXT};
            font-family: {cls.FONT_DISPLAY};
            font-size: 18px;
            font-weight: 800;
        }}
        #ChatHistoryList {{
            background: transparent;
            color: {cls.TEXT};
            border: 0;
            padding: 2px;
            font-family: {cls.FONT_BODY};
            font-size: 13px;
        }}
        #ChatHistoryList::item {{
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 9px;
            margin-bottom: 6px;
        }}
        #ChatHistoryList::item:hover {{
            background: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.22);
        }}
        #ChatHistoryList::item:selected {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.20);
            color: {cls.TEXT};
            font-weight: 700;
        }}
        QDialog {{
            background: {cls.DEEP_NAVY};
            color: {cls.TEXT};
            font-family: {cls.FONT_BODY};
        }}
        QDialog QLabel {{
            color: {cls.TEXT};
            font-size: 17px;
            font-weight: 700;
        }}
        QDialog QPlainTextEdit {{
            background: #121212;
            color: {cls.TEXT};
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 14px;
            padding: 10px;
            font-size: 18px;
            selection-background-color: {cls.PURPLE};
        }}
        QDialog QPushButton {{
            background: {cls.GREEN};
            color: {cls.TEXT};
            border: 0;
            border-radius: 14px;
            padding: 8px 16px;
            font-family: {cls.FONT_BODY};
            font-weight: 800;
        }}
        QDialog QPushButton:hover {{
            background: {cls.GREEN_HOVER};
        }}
        """
