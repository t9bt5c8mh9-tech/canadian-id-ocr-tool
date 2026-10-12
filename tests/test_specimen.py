import pytest
from PIL import Image

import main
import specimen_generator as sg


def test_specimen_is_marked(tmp_path):
    p = sg.generate_specimen(str(tmp_path / "s.png"), {"name": "DOE, JANE"})
    img = Image.open(p)
    assert img.size == (sg.W, sg.H)
    # red SPECIMEN marking present in the white area at the bottom
    assert any(px[0] > 150 and px[1] < 80 for px in img.crop((40, 520, 600, 560)).getdata())


def test_specimen_bad_format(tmp_path):
    with pytest.raises(ValueError):
        sg.generate_specimen(str(tmp_path / "s.exe"))


def test_cli_specimen(tmp_path):
    out = tmp_path / "c.png"
    assert main.main(["--make-specimen", str(out)]) == 0 and out.exists()


def test_reference_templates_exist():
    for name in sg.REFERENCE_IMAGES:
        path = sg.reference_image(name)
        img = Image.open(path)
        img.load()
        assert img.width >= 600 and img.height >= 400


def test_reference_fronts_are_jpeg():
    # the internet-downloaded front templates are JPEGs; rendered Ontario
    # fixtures are PNGs and are checked separately
    fronts = [n for n in sg.REFERENCE_IMAGES if n.startswith("license_front")]
    assert fronts, "at least one downloaded front template is expected"
    for name in fronts:
        with open(sg.reference_image(name), "rb") as fh:
            assert fh.read(2) == b"\xff\xd8"  # JPEG magic bytes


def test_reference_back_has_barcode_band():
    img = Image.open(sg.reference_image(sg.BACK_REFERENCE)).convert("L")
    # the barcode area must contain both dark bars and light gaps
    band = list(img.crop((80, 120, 900, 350)).getdata())
    assert min(band) < 60 and max(band) > 200


def test_ontario_references_present():
    # the realistic Ontario-style front and back fixtures are present and loadable
    for name in (sg.FRONT_REFERENCE, sg.BACK_REFERENCE):
        img = Image.open(sg.reference_image(name))
        img.load()
        assert img.size == (sg.W, sg.H)
