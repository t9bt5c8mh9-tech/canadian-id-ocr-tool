import numpy as np
import pytest
from PIL import Image

import ocr_processor
import pdf_generator


def test_preprocess_shape_and_binary():
    img = Image.fromarray(np.random.randint(0, 255, (50, 100, 3), dtype=np.uint8))
    out = ocr_processor.preprocess_image(img)
    assert out.ndim == 2 and out.shape[1] >= 1000
    assert set(np.unique(out)) <= {0, 255}


def test_load_image_errors(tmp_path):
    with pytest.raises(ocr_processor.OCRError):
        ocr_processor.load_image(str(tmp_path / "a.txt"))
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"nope")
    with pytest.raises(ocr_processor.OCRError):
        ocr_processor.load_image(str(bad))


def test_load_image_ok(tmp_path):
    p = tmp_path / "a.jpg"
    Image.new("RGB", (10, 10)).save(p)
    assert ocr_processor.load_image(str(p)).size == (10, 10)


def test_download_rejects_scheme():
    with pytest.raises(ocr_processor.OCRError):
        ocr_processor.download_image("file:///etc/passwd")


def test_pdf(tmp_path):
    out = tmp_path / "sub" / "r.pdf"
    pdf_generator.generate_report([("x.png", {"name": "José Ünder", "province": "ON", "errors": ["bad"]})], str(out))
    assert out.read_bytes().startswith(b"%PDF")


def test_edit_and_save(tmp_path):
    img = Image.new("RGB", (100, 50), (120, 120, 120))
    out = ocr_processor.edit_image(img, rotate=90, crop=(0, 0, 50, 50), contrast=1.5)
    assert out.size == (50, 50)
    with pytest.raises(ocr_processor.OCRError):
        ocr_processor.edit_image(img, crop=(0, 0, 500, 50))
    p = ocr_processor.save_image(img, str(tmp_path / "d" / "x.png"))
    assert ocr_processor.load_image(p).size == (100, 50)
    with pytest.raises(ocr_processor.OCRError):
        ocr_processor.save_image(img, str(tmp_path / "x.exe"))
