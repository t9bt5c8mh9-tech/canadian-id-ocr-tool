import data_extractor as de

SAMPLE = """ONTARIO
DRIVER'S LICENCE
Name: SMITH, JOHN
Licence No: A1234-56789-01234
Date of Birth: 1990-05-17
Expiry: 2099-05-17
Address: 123 MAIN ST
TORONTO ON M5V 2T6
"""


def test_extract_fields():
    d = de.extract_fields(SAMPLE)
    assert d["province"] == "ON"
    assert d["name"] == "SMITH, JOHN"
    assert d["license_number"] == "A12345678901234"
    assert d["date_of_birth"] == "1990-05-17"
    assert d["expiry_date"] == "2099-05-17"
    assert "M5V 2T6" in d["address"]
    assert d["errors"] == []


def test_empty_text():
    d = de.extract_fields("")
    assert all(d[f] is None for f in de.FIELDS)


def test_parse_date():
    assert de.parse_date("17 May 1990").isoformat() == "1990-05-17"
    assert de.parse_date("garbage") is None


def test_validation():
    assert de.validate_license("A1234-56789-01234", "ON")
    assert not de.validate_license("123", "ON")
    errs = de.validate_fields({"date_of_birth": "2999-01-01"})
    assert "Date of birth is in the future" in errs
    assert "ID is expired" in de.validate_fields({"expiry_date": "2000-01-01"})


def test_postal_province_fallback():
    assert de.detect_province("1 Rue X\nMontreal H2X 1Y4") == "QC"


def test_merge():
    m = de.merge_results({"name": "A", "errors": ["x"]}, {"name": "B", "address": "C", "errors": ["x"]})
    assert m["name"] == "A" and m["address"] == "C" and m["errors"] == ["x"]
