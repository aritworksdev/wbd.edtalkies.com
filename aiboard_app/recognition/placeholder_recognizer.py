"""Default handwriting recognizer used until a production OCR provider is selected."""

from aiboard_app.recognition.handwriting_recognizer import PlaceholderRecognizer

__all__ = ["PlaceholderRecognizer"]
