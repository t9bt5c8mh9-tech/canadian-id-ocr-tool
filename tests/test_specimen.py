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
