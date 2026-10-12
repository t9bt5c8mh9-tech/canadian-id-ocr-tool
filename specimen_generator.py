"""Generate clearly marked SPECIMEN test cards with fake data for OCR testing.

The SPECIMEN marking is always applied (diagonal stamp plus text in the white
areas) and cannot be disabled, so output can never pass as a real ID.
"""
import logging
import os

from PIL import Image, ImageDraw, ImageFont

import config

logger = logging.getLogger(__name__)

FAKE_DATA = {
    "province": "ON",
    "name": "SPECIMEN, SAMPLE",
    "license_number": "A1234-56789-01234",
    "date_of_birth": "1990-01-01",
    "expiry_date": "2099-01-01",
    "address": "123 SAMPLE ST, TORONTO ON M5V 2T6",
}
W, H = 1012, 638


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def generate_specimen(path, data=None):
    """Create a labelled specimen card image at `path` and return the path."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported output format: {ext or path}")
    d = {**FAKE_DATA, **(data or {})}
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 90], fill=(40, 90, 160))
    prov = config.PROVINCES.get(d["province"], d["province"]).upper()
    draw.text((30, 25), f"{prov} - SAMPLE DRIVER'S LICENCE", fill="white", font=_font(36))
    rows = [("Name:", d["name"]), ("Licence No:", d["license_number"]),
            ("Date of Birth:", d["date_of_birth"]), ("Expiry:", d["expiry_date"]),
            ("Address:", d["address"])]
    for i, (label, value) in enumerate(rows):
        draw.text((40, 130 + i * 70), f"{label} {value}", fill="black", font=_font(32))
    # Marking in the white (empty) areas.
    draw.text((40, 520), "SPECIMEN - NOT A VALID DOCUMENT", fill=(200, 0, 0), font=_font(40))
    draw.text((40, 575), "FAKE DATA FOR SOFTWARE TESTING ONLY", fill=(200, 0, 0), font=_font(28))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    stamp = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    ImageDraw.Draw(stamp).text((60, 20), "SPECIMEN", fill=(200, 0, 0, 110), font=_font(150))
    stamp = stamp.rotate(25, expand=True)
    overlay.paste(stamp, ((W - stamp.width) // 2, (H - stamp.height) // 2), stamp)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)
    logger.info("Specimen written to %s", path)
    return path
