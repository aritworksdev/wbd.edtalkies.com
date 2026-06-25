from __future__ import annotations

from typing import Any


def decode_grayscale(image_bytes: bytes) -> Any:
    import cv2
    import numpy as np

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("The image could not be decoded.")
    return image


def dark_text_on_light(image: Any) -> Any:
    """Normalize blackboards and documents to dark text on a light page."""
    import cv2

    # A dark average means the source is probably a blackboard with light ink.
    return cv2.bitwise_not(image) if float(image.mean()) < 127.0 else image


def normalized_color_image(image_bytes: bytes) -> Any:
    import cv2

    gray = dark_text_on_light(decode_grayscale(image_bytes))
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def document_variants(image_bytes: bytes) -> list[Any]:
    """Create OCR-friendly document variants for screenshots and photos."""
    import cv2

    gray = dark_text_on_light(decode_grayscale(image_bytes))
    height, width = gray.shape
    scale = max(1.0, 1800.0 / max(width, 1))
    if scale > 1.0:
        gray = cv2.resize(
            gray,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
    denoised = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    _, otsu = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(
        contrast,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )
    return [gray, contrast, otsu, adaptive]
