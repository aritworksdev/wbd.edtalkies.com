# AiBoard App

AiBoard App is a modular, full-screen Windows 10/11 smartboard whiteboard built with Python and PySide6. Teachers can draw with touch, stylus, or mouse; confirm recognized handwriting; type questions; send them to EdTalkies; and view rich AI responses.

The app works without API credentials. When `EDTALKIES_API_BASE_URL` is blank, it returns a clearly labeled mock response.

## Install on Windows

Python 3.12 (64-bit) is recommended because it is supported by the full local
OCR stack, including PaddlePaddle.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Install PaddleOCR (primary OCR)

In the activated Python 3.12 virtual environment:

```powershell
python --version
python -c "import platform; print(platform.architecture()[0]); print(platform.machine())"
pip install -r requirements-ocr-paddle.txt
```

PaddleOCR downloads its selected models on first use. If PaddlePaddle is not
available for the active Python version, AiBoard records the provider error and
continues with TrOCR.

PaddlePaddle's official Windows wheels support Python 3.9 through 3.13 and are
hosted on Paddle's package index rather than the default PyPI index. The
requirements file includes that official CPU index. Python 3.14 is not
currently supported.

Official references:

- [PaddleOCR installation and Python integration](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html)
- [TrOCR model documentation](https://huggingface.co/docs/transformers/model_doc/trocr)

### Install Tesseract (emergency local fallback)

Install Tesseract 5 for Windows, then configure its executable:

```env
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
TESSERACT_LANGUAGE=eng
```

The Python package alone is not enough; the native Tesseract application must
also be installed.

See the [official Tesseract installation documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html).

## Run

```powershell
python main.py
```

The app opens full-screen by default. For development, set `AIBOARD_FULLSCREEN=false` in `.env`.

## Upload and Extract Document Text

Select **Upload Document** from the toolbar. AiBoard extracts the content in a
background worker and places it in the same editable review panel used for
handwriting. Review the text, then select **Ask EdTalkies**.

Supported formats:

- PDF, including scanned PDFs through the OCR pipeline
- DOCX, including paragraphs and table cells
- TXT and Markdown
- HTML
- PNG, JPEG, BMP, and TIFF images

Large scanned PDFs can take time because every page must be rendered and
recognized. The board remains responsive and displays extraction status while
the work continues.

AiBoard automatically detects whether an uploaded image is a normal
black-text-on-white document or a light-on-dark board image before OCR.
Mixed PDFs preserve embedded text and OCR only scanned pages.

The recognized-text status line reports the selected OCR model, confidence,
and fallback chain, for example:

```text
OCR: Tesseract 5 (eng) | Confidence: 72% |
Fallbacks: PaddleOCR PP-OCRv5 (en) -> Tesseract 5 (eng)
```

For printed PNG/JPEG documents, PaddleOCR or Tesseract should normally produce
the best result. If the status shows TrOCR or `No local OCR model returned
text`, verify the PaddleOCR installation and `TESSERACT_CMD`. When Google
Vision is configured, low/empty local results expose **Use Google Vision OCR**.

PNG/JPEG document extraction uses a printed-document pipeline:

1. PaddleOCR
2. Enhanced Tesseract over multiple contrast/threshold variants
3. TrOCR only as a final fallback

At least PaddleOCR or the native Tesseract executable should be installed for
reliable printed PNG extraction. If neither is installed, the UI reports that
the printed-document providers are unavailable and offers Google Vision when
configured.

## Configure EdTalkies

Edit `.env`:

```env
EDTALKIES_API_BASE_URL=https://ramovies.app/edtalkies
EDTALKIES_API_KEY=
EDTALKIES_AI_QUERY_PATH=/api/AiBotTalkies/QuickAskAiTeacherAsync
EDTALKIES_OCR_PATH=/api/ocr/handwriting
EDTALKIES_DOWNLOAD_PATH=/api/AiBotTalkies/DownloadDocument
EDTALKIES_TIMEOUT_SECONDS=120
EDTALKIES_RETRY_COUNT=2
EDTALKIES_QUICKASK_CHANNEL=WEB
EDTALKIES_QUICKASK_PHONE=
EDTALKIES_QUICKASK_LANGUAGE=English
EDTALKIES_QUICKASK_SOURCE=SendPulse
EDTALKIES_QUICKASK_SEASON=Any Level
EDTALKIES_QUICKASK_GENRE=Any Subject
EDTALKIES_QUICKASK_CONTENT_SOURCE=Any Curriculum
```

Do not commit `.env`; it is ignored by Git.

The QuickAsk integration sends:

```json
{
  "Channel": "WEB",
  "Phone": "",
  "Message": "The reviewed teacher question",
  "Language": "English",
  "Source": "SendPulse",
  "Season": "Any Level",
  "Genre": "Any Subject",
  "ContentSource": "Any Curriculum"
}
```

The request and response contracts are isolated in
`aiboard_app/ai/edtalkies_client.py` and
`aiboard_app/ai/response_parser.py`.

OCR confidence and provider configuration:

```env
AIBOARD_LOCAL_HANDWRITING_MODEL=microsoft/trocr-base-handwritten
OCR_CONFIDENCE_HIGH=0.85
OCR_CONFIDENCE_MEDIUM=0.65
OCR_LANGUAGE=en
```

The local pipeline runs PaddleOCR first, uses Microsoft TrOCR when handwriting
quality is poor, and uses Tesseract as an emergency local fallback. TrOCR
downloads and caches its model on first use.

Allow roughly 2 GB of free disk space for Python OCR dependencies and cached
model files. Recognition runs on the CPU unless the installed PyTorch runtime
and Windows device support compatible acceleration.

Handwriting OCR is probabilistic and cannot guarantee 100% accuracy for every
writing style, pen thickness, or symbol. Write in clear horizontal lines and
review the editable recognized text before submitting it.

### Optional Google Vision fallback

```env
GOOGLE_VISION_ENABLED=false
GOOGLE_APPLICATION_CREDENTIALS=./config/google-vision-service-account.json
GOOGLE_CLOUD_PROJECT_ID=edtalkies
```

Relative credential paths such as `./config/google-vision-service-account.json`
are resolved from the AiBoard project directory, not from the terminal's
current directory.

When Google Vision is enabled and its credential file is valid, AiBoard calls
it automatically whenever the best local OCR confidence is below
`OCR_CONFIDENCE_HIGH` (85% by default). If Google Vision fails, the strongest
local result remains editable and the cloud error appears in the OCR
diagnostics. The manual **Use Google Vision OCR** action remains available for
another attempt on low-confidence image or scanned-PDF results.

If Google is not called, the OCR status now displays the exact reason, such as:

```text
Google Vision skipped: GOOGLE_VISION_ENABLED is false
```

or:

```text
Google Vision skipped: credential file not found: .../config/google-vision-service-account.json
```

Copy
`config/google-vision-service-account.example.json.template` to
`config/google-vision-service-account.json`, then replace every placeholder
with values from a Google Cloud service-account key. The real JSON is ignored
by Git through `config/*.json` and must never be committed.

The credential JSON must contain `type`, `project_id`, `private_key_id`,
`private_key`, `client_email`, `client_id`, `auth_uri`, `token_uri`,
`auth_provider_x509_cert_url`, `client_x509_cert_url`, and
`universe_domain`. See the
[official Google Vision OCR guide](https://cloud.google.com/vision/docs/ocr).

## OCR Confidence Workflow

1. PaddleOCR runs first.
2. If PaddleOCR is unavailable or below the high-confidence threshold, TrOCR
   evaluates the handwriting.
3. If the primary local models fail or remain low confidence, Tesseract runs.
4. AiBoard selects the strongest local result.
5. If the strongest local result is below 85%, Google Vision runs
   automatically when enabled with valid credentials.

- **85% and above:** normal editable text; **Ask EdTalkies** is enabled.
- **65%–84%:** uncertain words are highlighted and confirmation is required.
- **Below 65%:** submission is blocked until the teacher rewrites, edits the
  text, or explicitly uses Google Vision OCR.

## Current Features

- Full-screen touch-friendly whiteboard with mouse and stylus support
- Pen color and thickness, eraser, clear, undo, redo, and PNG save
- A two-stage **Ask AI** flow: the first click converts the current board into
  editable text; after review, the second click submits it to the API
- Confidence-aware OCR pipeline: PaddleOCR → TrOCR → Tesseract
- Optional, explicit Google Vision fallback for low-confidence recognition
- Uncertain-word highlighting and editable text before every API submission
- Keyboard question entry using the same visible review/API flow
- Document upload and editable text extraction for PDF, DOCX, text, Markdown,
  HTML, images, and scanned PDFs
- Background API and download operations so the UI remains responsive
- Configurable EdTalkies API client with timeout, OCR retries, IDs, and mock mode
- Rich text/HTML response panel with scrolling, copy, save, and document actions
- Safe Windows quit, shutdown, and restart behavior with confirmation
- Placeholder voice, camera, and gesture providers
- File and console logging under the configured export directory

## API Contract Integration Points

When the final EdTalkies contract is available, update:

- `aiboard_app/ai/edtalkies_client.py` for request URLs, headers, authentication, and payloads
- `aiboard_app/ai/response_parser.py` for response fields and attachment metadata
- `aiboard_app/recognition/edtalkies_ocr_provider.py` for OCR response fields

The UI should not need to change.

## Exit Configuration

```env
AIBOARD_EXIT_ACTION=quit
AIBOARD_CONFIRM_EXIT=true
```

`AIBOARD_EXIT_ACTION` accepts `quit`, `shutdown`, or `reboot`. Keep confirmation enabled for classroom devices.

## Tests

```powershell
pytest
```

OCR, document extraction, and API requests run outside the Qt UI thread. The
application uses a non-modal busy status instead of blocking the board with a
modal loading dialog.

## Suggested Next Milestone

Finalize the EdTalkies request/response contract, add contract fixtures and integration tests, then integrate Windows Ink handwriting recognition. After that, package the app with PyInstaller or MSIX and add a signed installer plus kiosk-mode deployment documentation.
