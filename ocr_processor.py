"""Image loading, preprocessing and OCR."""
import logging
import os
from io import BytesIO
from urllib.parse import urlparse

import cv2
import numpy as np
import pytesseract
import requests
from PIL import Image, ImageEnhance, UnidentifiedImageError

import config

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Raised when an image cannot be loaded or processed."""


def load_image(path):
    """Load an image file as a PIL RGB image."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise OCRError(f"Unsupported image format: {ext or path}")
    try:
        with Image.open(path) as img:
            return img.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise OCRError(f"Cannot open image {path}: {exc}") from exc


def download_image(url):
    """Download an image from an http(s) URL and return a PIL RGB image."""
    if urlparse(url).scheme not in ("http", "https"):
        raise OCRError("Only http(s) URLs are supported")
    try:
        response = requests.get(url, timeout=config.DOWNLOAD_TIMEOUT, stream=True)
        response.raise_for_status()
        content = response.raw.read(config.MAX_DOWNLOAD_BYTES + 1, decode_content=True)
        if len(content) > config.MAX_DOWNLOAD_BYTES:
            raise OCRError("Downloaded image is too large")
        with Image.open(BytesIO(content)) as img:
            return img.convert("RGB")
    except requests.RequestException as exc:
        raise OCRError(f"Failed to download {url}: {exc}") from exc
    except (OSError, UnidentifiedImageError) as exc:
        raise OCRError(f"URL did not return a valid image: {exc}") from exc


def preprocess_image(image):
    """Grayscale, upscale, denoise and threshold; returns a numpy array."""
    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    if gray.shape[1] < config.MIN_OCR_WIDTH:
        scale = config.MIN_OCR_WIDTH / gray.shape[1]
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return thresh


def extract_text(image):
    """Run OCR on a PIL image and return the text."""
    processed = preprocess_image(image)
    try:
        return pytesseract.image_to_string(
            processed, lang=config.TESSERACT_LANG, config=config.TESSERACT_CONFIG
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError("Tesseract is not installed or not on PATH") from exc
    except pytesseract.TesseractError as exc:
        raise OCRError(f"OCR failed: {exc}") from exc


def edit_image(image, rotate=0, crop=None, brightness=1.0, contrast=1.0):
    """Apply scan-quality adjustments (rotate, crop, brightness, contrast).

    `crop` is a (left, upper, right, lower) pixel box. Returns a new image.
    """
    if crop:
        left, upper, right, lower = crop
        if not (0 <= left < right <= image.width and 0 <= upper < lower <= image.height):
            raise OCRError(f"Invalid crop box {crop} for image size {image.size}")
        image = image.crop(crop)
    if rotate:
        image = image.rotate(-rotate, expand=True, fillcolor=(255, 255, 255))
    if brightness != 1.0:
        image = ImageEnhance.Brightness(image).enhance(brightness)
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    return image


def save_image(image, path):
    """Save an image (format chosen from the extension); returns the path."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise OCRError(f"Unsupported output format: {ext or path}")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        image.save(path)
    except OSError as exc:
        raise OCRError(f"Cannot save image {path}: {exc}") from exc
    logger.info("Saved image to %s", path)
    return path


def get_image(source):
    """Load an image from a file path or URL."""
    if source.lower().startswith(("http://", "https://")):
        return download_image(source)
    return load_image(source)


def process_source(source, edits=None, save_to=None):
    """OCR a file path or URL, optionally editing and saving the image first."""
    logger.info("Processing %s", source)
    image = get_image(source)
    if edits:
        image = edit_image(image, **edits)
    if save_to:
        save_image(image, save_to)
    return extract_text(image)
