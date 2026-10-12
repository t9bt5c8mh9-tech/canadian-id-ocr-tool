"""Generate clearly marked SPECIMEN test cards with fake data for OCR testing.

The SPECIMEN marking is always applied (diagonal stamp plus text in the white
areas) and cannot be disabled, so output can never pass as a real ID.

Realistic card dimensions and layout are based on the internet reference
templates stored in ``samples/`` (see ``samples/README.md``).
"""
import logging
import os

from PIL import Image, ImageDraw, ImageFont

import config

logger = logging.getLogger(__name__)

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")

FAKE_DATA = {
    "province": "ON",
    "name": "SPECIMEN, SAMPLE",
    "license_number": "A1234-56789-01234",
    "date_of_birth": "1990-01-01",
    "sex": "X",
    "height": "170 cm",
    "address": "123 SAMPLE ST, TORONTO ON M5V 2T6",
    "license_class": "G",
    "issue_date": "2020-01-01",
    "expiry_date": "2099-01-01",
}
W, H = 1012, 638

# Realistic reference fixtures committed in samples/ (see samples/README.md).
# The Ontario-style front/back are locally rendered SPECIMEN cards whose field
# layout mirrors a real Ontario licence; the US fronts are internet-sourced
# official "SAMPLE" images.
REFERENCE_IMAGES = ("ontario_sample_front.png", "ontario_sample_back.png",
                    "license_front_reference_1.jpg", "license_front_reference_2.jpg",
                    "license_back_reference.png")

FRONT_REFERENCE = "ontario_sample_front.png"
BACK_REFERENCE = "ontario_sample_back.png"


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def reference_image(name):
    """Return the path of a downloaded reference template in samples/."""
    return os.path.join(SAMPLES_DIR, name)


def generate_specimen(path, data=None):
    """Create a labelled specimen card image at `path` and return the path.

    The layout mirrors a real Ontario licence front (photo box on the left,
    labelled fields on the right) while using only fake data.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported output format: {ext or path}")
    d = {**FAKE_DATA, **(data or {})}
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 88], fill=(26, 84, 144))
    prov = config.PROVINCES.get(d["province"], d["province"]).upper()
    draw.text((28, 24), f"{prov} - SAMPLE DRIVER'S LICENCE", fill="white", font=_font(36))
    # Photo placeholder box on the left.
    draw.rectangle([40, 130, 300, 470], fill=(225, 228, 232), outline=(150, 150, 150))
    draw.text((120, 290), "PHOTO", fill=(120, 120, 120), font=_font(28))
    # Labelled fields on the right, mirroring a real Ontario card. Labels use
    # the bilingual wording but keep "Name:", "Licence No:" etc. so the OCR
    # extractor can read the value on the same line.
    rows = [("Name / Nom:", d["name"]),
            ("Licence No / No de permis:", d["license_number"]),
            ("Date of Birth / Naissance:", d["date_of_birth"]),
            ("Expiry / Expire:", d["expiry_date"]),
            ("Address / Adresse:", d["address"]),
            ("Class / Categorie:", d["license_class"])]
    y = 130
    for label, value in rows:
        draw.text((330, y), f"{label} {value}", fill="black", font=_font(28))
        y += 62
    # Marking in the white (empty) areas.
    draw.rectangle([40, 500, W - 40, 600], outline=(200, 0, 0), width=3)
    draw.text((60, 516), "SPECIMEN - NOT A VALID DOCUMENT", fill=(200, 0, 0), font=_font(34))
    draw.text((60, 560), "FAKE DATA FOR SOFTWARE TESTING ONLY", fill=(200, 0, 0), font=_font(24))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stamp = Image.new("RGBA", (520, 160), (0, 0, 0, 0))
    ImageDraw.Draw(stamp).text((10, 10), "SPECIMEN", fill=(200, 0, 0, 90), font=_font(90))
    stamp = stamp.rotate(18, expand=True)
    # Confine the diagonal stamp to the photo placeholder so the card is
    # unmistakably marked but the text fields stay machine-readable.
    overlay.paste(stamp, (50, 250), stamp)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)
    logger.info("Specimen written to %s", path)
    return path
