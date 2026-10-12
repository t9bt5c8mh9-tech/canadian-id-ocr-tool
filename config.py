"""Configuration and constants for the Canadian ID OCR tool."""
import logging
import re

SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")
TESSERACT_LANG = "eng"
TESSERACT_CONFIG = "--psm 6"
MIN_OCR_WIDTH = 1000  # upscale smaller images to this width
DOWNLOAD_TIMEOUT = 15  # seconds
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_FILE = "id_ocr.log"
DEFAULT_REPORT_DIR = "reports"

PROVINCES = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

# Extra spellings (incl. French) mapped to province codes.
PROVINCE_ALIASES = {
    "QUEBEC": "QC",
    "QUÉBEC": "QC",
    "NEWFOUNDLAND": "NL",
    "PRINCE EDWARD ISLAND": "PE",
    "YUKON TERRITORY": "YT",
}

# Licence number patterns per province (applied after removing spaces/dashes).
LICENSE_PATTERNS = {
    "ON": re.compile(r"^[A-Z]\d{14}$"),
    "QC": re.compile(r"^[A-Z]\d{12}$"),
    "AB": re.compile(r"^\d{6,9}$"),
    "BC": re.compile(r"^\d{7,8}$"),
    "MB": re.compile(r"^[A-Z0-9]{12,14}$"),
    "SK": re.compile(r"^\d{8}$"),
    "NS": re.compile(r"^[A-Z]{1,5}\d{9}$"),
    "NB": re.compile(r"^\d{5,7}$"),
    "PE": re.compile(r"^\d{5,6}$"),
    "NL": re.compile(r"^[A-Z]\d{9}$"),
}
GENERIC_LICENSE_PATTERN = re.compile(r"^[A-Z0-9]{5,15}$")

POSTAL_CODE_RE = re.compile(r"\b([ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z])\s?(\d[ABCEGHJ-NPRSTV-Z]\d)\b")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y %m %d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%b %d %Y", "%Y%m%d")


def setup_logging(level=logging.INFO, log_file=LOG_FILE):
    """Configure root logging to console and (optionally) a file."""
    handlers = [logging.StreamHandler()]
    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError:
            pass
    logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers, force=True)
