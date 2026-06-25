from __future__ import annotations

import io

from PIL import Image, ImageDraw

from aiboard_app.recognition.image_preprocessor import (
    dark_text_on_light,
    decode_grayscale,
    document_variants,
)


def _png(background: str, foreground: str) -> bytes:
    image = Image.new("L", (200, 100), background)
    ImageDraw.Draw(image).rectangle((40, 30, 160, 70), fill=foreground)
    stream = io.BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


def test_white_document_is_not_inverted() -> None:
    original = decode_grayscale(_png("white", "black"))
    normalized = dark_text_on_light(original)

    assert normalized[0, 0] > normalized[50, 100]


def test_blackboard_is_inverted_to_document_polarity() -> None:
    original = decode_grayscale(_png("black", "white"))
    normalized = dark_text_on_light(original)

    assert normalized[0, 0] > normalized[50, 100]


def test_document_variants_upscale_small_images() -> None:
    variants = document_variants(_png("white", "black"))

    assert len(variants) == 4
    assert variants[0].shape[1] >= 1800
