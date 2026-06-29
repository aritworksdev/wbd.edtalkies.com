from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - convenience before dependencies are installed.
    def load_dotenv(*args, **kwargs) -> bool:  # type: ignore[no-redef]
        return False


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}.") from exc


@dataclass(frozen=True)
class EdTalkiesSettings:
    api_base_url: str
    api_key: str
    ai_query_path: str
    ocr_path: str
    timeout_seconds: int
    retry_count: int
    model: str
    assistant_mode: str
    school_id: str
    board_id: str
    device_id: str
    session_id: str = ""
    quick_ask_channel: str = "WEB"
    quick_ask_phone: str = ""
    quick_ask_language: str = "English"
    quick_ask_source: str = "SendPulse"
    quick_ask_season: str = "Any Level"
    quick_ask_genre: str = "Any Subject"
    quick_ask_content_source: str = "Any Curriculum"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_base_url.strip())

    def build_url(self, path: str) -> str:
        base = self.api_base_url.rstrip("/")
        route = path if path.startswith("/") else f"/{path}"
        return f"{base}{route}"


@dataclass(frozen=True)
class AppSettings:
    app_env: str
    fullscreen: bool
    export_dir: Path
    handwriting_provider: str
    exit_action: str
    confirm_exit: bool
    log_level: str
    edtalkies: EdTalkiesSettings
    local_handwriting_model: str = "microsoft/trocr-base-handwritten"
    ocr_confidence_high: float = 0.85
    ocr_confidence_medium: float = 0.65
    ocr_language: str = "en"
    tesseract_cmd: str = ""
    tesseract_language: str = "eng"
    google_vision_enabled: bool = False
    google_application_credentials: Path = Path("config/google-vision-service-account.json")
    google_cloud_project_id: str = ""


def load_settings(env_file: str | Path | None = None) -> AppSettings:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    export_dir = Path(os.getenv("AIBOARD_EXPORT_DIR", "~/AiBoard/exports")).expanduser()
    provider = os.getenv("AIBOARD_HANDWRITING_PROVIDER", "local").lower()
    # Early releases generated .env files with mock enabled. Silently migrate
    # those installations to real OCR unless mock mode is explicitly allowed.
    if provider == "mock" and not _bool_env("AIBOARD_ALLOW_MOCK_RECOGNIZER", False):
        provider = "local"
    high_confidence = _float_env("OCR_CONFIDENCE_HIGH", 0.85)
    medium_confidence = _float_env("OCR_CONFIDENCE_MEDIUM", 0.65)
    if not 0 <= medium_confidence < high_confidence <= 1:
        raise ValueError(
            "OCR confidence thresholds must satisfy "
            "0 <= OCR_CONFIDENCE_MEDIUM < OCR_CONFIDENCE_HIGH <= 1."
        )
    project_root = Path(__file__).resolve().parents[2]
    credentials_path = Path(
        os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "./config/google-vision-service-account.json",
        )
    ).expanduser()
    if not credentials_path.is_absolute():
        credentials_path = (project_root / credentials_path).resolve()

    return AppSettings(
        app_env=os.getenv("AIBOARD_APP_ENV", "production"),
        fullscreen=_bool_env("AIBOARD_FULLSCREEN", True),
        export_dir=export_dir,
        handwriting_provider=provider,
        exit_action=os.getenv("AIBOARD_EXIT_ACTION", "quit").lower(),
        confirm_exit=_bool_env("AIBOARD_CONFIRM_EXIT", True),
        log_level=os.getenv("AIBOARD_LOG_LEVEL", "INFO").upper(),
        edtalkies=EdTalkiesSettings(
            api_base_url=os.getenv(
                "EDTALKIES_API_BASE_URL",
                "https://ramovies.app/edtalkies",
            ),
            api_key=os.getenv("EDTALKIES_API_KEY", ""),
            ai_query_path=os.getenv(
                "EDTALKIES_AI_QUERY_PATH",
                "/api/AiBotTalkies/QuickAskAiTeacherAsync",
            ),
            ocr_path=os.getenv("EDTALKIES_OCR_PATH", "/api/ocr/handwriting"),
            timeout_seconds=_int_env("EDTALKIES_TIMEOUT_SECONDS", 120),
            retry_count=_int_env("EDTALKIES_RETRY_COUNT", 2),
            model=os.getenv("EDTALKIES_MODEL", "default"),
            assistant_mode=os.getenv("EDTALKIES_ASSISTANT_MODE", "teacher_board"),
            school_id=os.getenv("EDTALKIES_SCHOOL_ID", ""),
            board_id=os.getenv("EDTALKIES_BOARD_ID", ""),
            device_id=os.getenv("EDTALKIES_DEVICE_ID", ""),
            session_id=os.getenv("EDTALKIES_SESSION_ID", ""),
            quick_ask_channel=os.getenv("EDTALKIES_QUICKASK_CHANNEL", "WEB"),
            quick_ask_phone=os.getenv("EDTALKIES_QUICKASK_PHONE", ""),
            quick_ask_language=os.getenv("EDTALKIES_QUICKASK_LANGUAGE", "English"),
            quick_ask_source=os.getenv("EDTALKIES_QUICKASK_SOURCE", "SendPulse"),
            quick_ask_season=os.getenv("EDTALKIES_QUICKASK_SEASON", "Any Level"),
            quick_ask_genre=os.getenv("EDTALKIES_QUICKASK_GENRE", "Any Subject"),
            quick_ask_content_source=os.getenv(
                "EDTALKIES_QUICKASK_CONTENT_SOURCE",
                "Any Curriculum",
            ),
        ),
        local_handwriting_model=os.getenv(
            "AIBOARD_LOCAL_HANDWRITING_MODEL",
            "microsoft/trocr-base-handwritten",
        ),
        ocr_confidence_high=high_confidence,
        ocr_confidence_medium=medium_confidence,
        ocr_language=os.getenv("OCR_LANGUAGE", "en"),
        tesseract_cmd=os.getenv("TESSERACT_CMD", ""),
        tesseract_language=os.getenv("TESSERACT_LANGUAGE", "eng"),
        google_vision_enabled=_bool_env("GOOGLE_VISION_ENABLED", False),
        google_application_credentials=credentials_path,
        google_cloud_project_id=os.getenv("GOOGLE_CLOUD_PROJECT_ID", ""),
    )
