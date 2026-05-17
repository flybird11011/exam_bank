from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:  # pragma: no cover - optional fallback when OCR deps are absent
    RapidOCR = None


_NUMERIC_TEXT_RE = re.compile(r"^\d+(?:\.\d+)?%?$")
_SMALL_TEXT_RE = re.compile(r"^[\w\u00B7\u00B1\u2212\u03B1-\u03C9\u0391-\u03A9\u2220\u0394\u25B3\u2032\u2033.,=+\-×÷/^()]+$")


@lru_cache(maxsize=1)
def _get_ocr_engine():
    if RapidOCR is None:
        return None
    return RapidOCR()


def _prepare_variants(image: Image.Image) -> list[Image.Image]:
    variants: list[Image.Image] = []
    base = image.convert("L")

    for threshold in (200, 190, 180, 170, 160, 150):
        bw = base.point(lambda p, t=threshold: 255 if p > t else 0).convert("L")
        bw = ImageOps.invert(bw)
        bbox = bw.getbbox()
        if bbox is None:
            continue
        cropped = bw.crop(bbox)
        canvas = Image.new("L", (cropped.width + 20, cropped.height + 20), 0)
        canvas.paste(cropped, (10, 10))
        variants.append(canvas.resize((canvas.width * 20, canvas.height * 20), Image.Resampling.LANCZOS))

    contrast = ImageOps.autocontrast(base)
    contrast = contrast.filter(ImageFilter.SHARPEN)
    contrast = ImageEnhance.Contrast(contrast).enhance(2.0)
    contrast = contrast.resize((contrast.width * 20, contrast.height * 20), Image.Resampling.LANCZOS)
    variants.append(contrast)

    return variants


def _normalize_text(text: str) -> str:
    return text.strip().replace(" ", "")


def recognize_small_numeric_image(image_path: str | Path) -> str | None:
    path = Path(image_path)
    if not path.exists():
        return None

    try:
        image = Image.open(path)
    except OSError:
        return None

    if max(image.size) > 40 or image.width * image.height > 1600:
        return None

    engine = _get_ocr_engine()
    if engine is None:
        return None

    best_text: str | None = None
    best_rank = (-1, -1, -1, 0.0)

    for variant in _prepare_variants(image):
        result, _elapsed = engine(variant)
        if not result:
            continue

        for _box, text, confidence in result:
            normalized_text = _normalize_text(str(text))
            if not normalized_text:
                continue
            if not _NUMERIC_TEXT_RE.fullmatch(normalized_text):
                continue
            rank = (
                1 if "%" in normalized_text else 0,
                1 if "." in normalized_text else 0,
                len(normalized_text),
                float(confidence),
            )
            if rank >= best_rank:
                best_text = normalized_text
                best_rank = rank

    return best_text


def recognize_small_text_image(image_path: str | Path) -> str | None:
    path = Path(image_path)
    if not path.exists():
        return None

    try:
        image = Image.open(path)
    except OSError:
        return None

    if max(image.size) > 40 or image.width * image.height > 1600:
        return None

    engine = _get_ocr_engine()
    if engine is None:
        return None

    best_text: str | None = None
    best_rank = (-1, -1, -1, 0.0)

    for variant in _prepare_variants(image):
        result, _elapsed = engine(variant)
        if not result:
            continue

        for _box, text, confidence in result:
            normalized_text = _normalize_text(str(text))
            if not normalized_text:
                continue
            if not _SMALL_TEXT_RE.fullmatch(normalized_text):
                continue
            rank = (
                1 if any(ch.isdigit() for ch in normalized_text) else 0,
                len(normalized_text),
                1 if any(ch.isascii() for ch in normalized_text) else 0,
                float(confidence),
            )
            if rank >= best_rank:
                best_text = normalized_text
                best_rank = rank

    return best_text
