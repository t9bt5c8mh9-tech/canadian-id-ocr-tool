"""PDF report generation."""
import logging
import os
from datetime import datetime

from fpdf import FPDF

import config
from data_extractor import FIELDS

logger = logging.getLogger(__name__)

_LABELS = {
    "name": "Name",
    "date_of_birth": "Date of Birth",
    "license_number": "License/ID Number",
    "address": "Address",
    "expiry_date": "Expiration Date",
    "province": "Issuing Province",
}


def _safe(text):
    """fpdf core fonts only support latin-1."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def generate_report(results, output_path):
    """Write a PDF report. `results` is a list of (source, data) tuples."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Canadian ID OCR Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Generated {datetime.now():%Y-%m-%d %H:%M:%S}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for source, data in results:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _safe(f"Source: {source}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for field in FIELDS:
            value = data.get(field)
            if field == "province" and value in config.PROVINCES:
                value = f"{config.PROVINCES[value]} ({value})"
            pdf.multi_cell(0, 6, _safe(f"{_LABELS[field]}: {value or 'N/A'}"), new_x="LMARGIN", new_y="NEXT")
        for err in data.get("errors", []):
            pdf.set_text_color(180, 0, 0)
            pdf.multi_cell(0, 6, _safe(f"Warning: {err}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
    directory = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(directory, exist_ok=True)
    pdf.output(output_path)
    logger.info("Report written to %s", output_path)
    return output_path
