from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.parser.small_image_ocr import recognize_small_numeric_image, recognize_small_text_image


def test_recognize_small_numeric_image_extracts_percentage():
    font_path = Path("C:/Windows/Fonts/ARIALN.TTF")
    font = ImageFont.truetype(str(font_path), size=10)

    image = Image.new("L", (38, 14), 255)
    draw = ImageDraw.Draw(image)
    draw.text((2, 1), "11.5%", fill=0, font=font)

    temp_dir = Path(__file__).resolve().parent / "_tmp"
    temp_dir.mkdir(exist_ok=True)
    image_path = temp_dir / "numeric.png"
    image.save(image_path)

    assert recognize_small_numeric_image(image_path) == "11.5%"


def test_recognize_small_text_image_extracts_short_formula_like_text():
    font_path = Path("C:/Windows/Fonts/ARIAL.TTF")
    font = ImageFont.truetype(str(font_path), size=12)

    image = Image.new("L", (40, 16), 255)
    draw = ImageDraw.Draw(image)
    draw.text((2, 0), "AB", fill=0, font=font)

    temp_dir = Path(__file__).resolve().parent / "_tmp"
    temp_dir.mkdir(exist_ok=True)
    image_path = temp_dir / "alpha-beta.png"
    image.save(image_path)

    assert recognize_small_text_image(image_path) == "AB"
