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
