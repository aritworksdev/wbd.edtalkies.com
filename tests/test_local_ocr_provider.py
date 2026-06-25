from __future__ import annotations

import io

from PIL import Image, ImageDraw

from aiboard_app.recognition.local_ocr_provider import LocalOcrProvider


def _blackboard_image() -> bytes:
    image = Image.new("RGB", (600, 240), "black")
    draw = ImageDraw.Draw(image)
    draw.line((30, 60, 300, 60), fill="white", width=8)
    draw.line((40, 150, 420, 150), fill="white", width=8)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_extract_handwritten_lines_from_blackboard_image() -> None:
    lines = LocalOcrProvider._extract_handwritten_lines(_blackboard_image())

    assert len(lines) == 2
    assert all(line.mode == "RGB" for line in lines)
    # TrOCR input is normalized to dark writing on a light background.
    assert lines[0].getpixel((0, 0)) == (255, 255, 255)


def test_contiguous_ranges_filters_small_noise() -> None:
    ranges = LocalOcrProvider._contiguous_ranges(
        [False, True, False, False, True, True, True, False],
        minimum_size=2,
    )
    assert ranges == [(4, 7)]
