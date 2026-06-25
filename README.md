# AiBoard App

AiBoard App is a modular, full-screen Windows 10/11 smartboard whiteboard built with Python and PySide6. Teachers can draw with touch, stylus, or mouse; confirm recognized handwriting; type questions; send them to EdTalkies; and view rich AI responses.

The app works without API credentials. When `EDTALKIES_API_BASE_URL` is blank, it returns a clearly labeled mock response.

## Install on Windows

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

```powershell
python main.py
```

The app opens full-screen by default. For development, set `AIBOARD_FULLSCREEN=false` in `.env`.

## Configure EdTalkies

Edit `.env`:

```env
EDTALKIES_API_BASE_URL=https://your-edtalkies-host.example
EDTALKIES_API_KEY=your-secret-key
EDTALKIES_AI_QUERY_PATH=/api/ai/query
EDTALKIES_OCR_PATH=/api/ocr/handwriting
EDTALKIES_TIMEOUT_SECONDS=30
EDTALKIES_RETRY_COUNT=2
EDTALKIES_DEVICE_ID=board-01
EDTALKIES_SCHOOL_ID=school-01
EDTALKIES_SESSION_ID=
```

Do not commit `.env`; it is ignored by Git.

Real local handwriting recognition is enabled by default:

```env
AIBOARD_HANDWRITING_PROVIDER=local
AIBOARD_LOCAL_HANDWRITING_MODEL=microsoft/trocr-base-handwritten
AIBOARD_AUTO_RECOGNIZE=true
AIBOARD_AUTO_RECOGNIZE_DELAY_MS=1800
```

The local provider uses Microsoft's TrOCR handwritten model. On first use it
downloads the model and caches it on the Windows device; this can take several
minutes depending on the connection. Later recognition runs from the local
cache and does not send the board image to an OCR service.

Allow roughly 2 GB of free disk space for Python OCR dependencies and cached
model files. Recognition runs on the CPU unless the installed PyTorch runtime
and Windows device support compatible acceleration.

For real handwriting conversion through the EdTalkies OCR endpoint:

```env
AIBOARD_HANDWRITING_PROVIDER=edtalkies
EDTALKIES_API_BASE_URL=https://your-edtalkies-host.example
EDTALKIES_OCR_PATH=/api/ocr/handwriting
```

Use `edtalkies` to send the board image to the configured EdTalkies OCR
endpoint. Use `mock` only for UI testing; it does not read handwriting.

Old `.env` files may still contain `AIBOARD_HANDWRITING_PROVIDER=mock`.
AiBoard now migrates that value to local OCR unless
`AIBOARD_ALLOW_MOCK_RECOGNIZER=true` is explicitly configured.

## Current Features

- Full-screen touch-friendly whiteboard with mouse and stylus support
- Pen color and thickness, eraser, clear, undo, redo, and PNG save
- A separate **Handwriting to Text** action that displays recognized text in
  an editable panel before **Ask AI** can submit it
- Automatic conversion after mouse or stylus writing pauses, with recognized
  text placed directly in the editable text box
- Real local handwriting OCR with blackboard preprocessing and multiline
  recognition using TrOCR
- Keyboard question entry using the same visible review/API flow
- Background API and download operations so the UI remains responsive
- Configurable EdTalkies API client with timeout, retries, IDs, and mock mode
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

## Suggested Next Milestone

Finalize the EdTalkies request/response contract, add contract fixtures and integration tests, then integrate Windows Ink handwriting recognition. After that, package the app with PyInstaller or MSIX and add a signed installer plus kiosk-mode deployment documentation.
