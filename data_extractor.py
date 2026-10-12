"""Parse and validate fields from OCR text of Canadian IDs."""
import re
from datetime import date, datetime

import config

FIELDS = ("name", "date_of_birth", "license_number", "address", "expiry_date", "province")

_DATE_RE = re.compile(
    r"(\d{4}[-/ ]\d{2}[-/ ]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{1,2} [A-Za-z]{3} \d{4}|[A-Za-z]{3} \d{1,2},? \d{4})"
)
_LICENSE_LABEL_RE = re.compile(
    r"\b(?:licen[sc]e|permis|dl|id)\b(?:[\s/]*[A-Za-zÀ-ÿ°.]+)*?\s*[:#]\s*([A-Z0-9][A-Z0-9 \-]{4,20})", re.I
)
_LICENSE_LOOSE_RE = re.compile(r"\b([A-Z]\d{4}[- ]?\d{5}[- ]?\d{5})\b")


def parse_date(value):
    """Parse a date string into a date, or return None."""
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value.strip().replace(",", ""))
    for fmt in config.DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def normalize_license(value):
    return re.sub(r"[\s\-]", "", value or "").upper()


def detect_province(text):
    """Return a province code found in the text, or None."""
    upper = text.upper()
    for name_, code in config.PROVINCE_ALIASES.items():
        if name_ in upper:
            return code
    for code, name_ in sorted(config.PROVINCES.items(), key=lambda kv: -len(kv[1])):
        if name_.upper() in upper:
            return code
    m = config.POSTAL_CODE_RE.search(upper)
    if m:
        first = m.group(1)[0]
        by_letter = {"A": "NL", "B": "NS", "C": "PE", "E": "NB", "G": "QC", "H": "QC", "J": "QC",
                     "K": "ON", "L": "ON", "M": "ON", "N": "ON", "P": "ON", "R": "MB",
                     "S": "SK", "T": "AB", "V": "BC", "Y": "YT"}
        if first in by_letter:
            return by_letter[first]
    return None


def validate_license(number, province=None):
    """Validate a licence number against the province format (generic if unknown)."""
    norm = normalize_license(number)
    pattern = config.LICENSE_PATTERNS.get(province, config.GENERIC_LICENSE_PATTERN)
    return bool(pattern.match(norm))


def _after_label(lines, labels):
    """Value following a label on the same line, or on the next line.

    Handles bilingual labels like "Name / Nom:" and "Address / Adresse:" by
    allowing extra label words (including a French translation after a slash)
    before the colon that precedes the value.
    """
    label_re = re.compile(
        r"^\s*(?:%s)\b(?:[\s/]*[A-Za-zÀ-ÿ]+)*\s*[:\-]\s*(.*)$" % "|".join(labels), re.I)
    for i, line in enumerate(lines):
        m = label_re.match(line)
        if m:
            value = m.group(1).strip()
            if value:
                return value
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
    return None


def extract_fields(text):
    """Extract fields from OCR text. Returns dict with fields plus 'errors' list."""
    text = text or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    data = {f: None for f in FIELDS}
    errors = []

    data["province"] = detect_province(text)

    name = _after_label(lines, ["name", "nom", "full name"])
    if not name:
        first = _after_label(lines, ["first name", "given names?", "prénom"])
        last = _after_label(lines, ["last name", "surname"])
        if first or last:
            name = " ".join(p for p in (first, last) if p)
    if name:
        data["name"] = re.sub(r"[^A-Za-z'\-,. À-ÿ]", "", name).strip() or None

    dob = _after_label(lines, ["date of birth", "dob", "birth", "naissance", "born"])
    exp = _after_label(lines, ["expiry", "expires", "exp", "expiration", "expiry date", "valid until"])
    for key, raw in (("date_of_birth", dob), ("expiry_date", exp)):
        if raw:
            m = _DATE_RE.search(raw)
            d = parse_date(m.group(1)) if m else None
            if d:
                data[key] = d.isoformat()
            else:
                errors.append(f"Could not parse {key}: {raw!r}")

    for line in lines:
        m = _LICENSE_LABEL_RE.search(line)
        if m and re.search(r"\d", m.group(1)):
            data["license_number"] = normalize_license(m.group(1))
            break
    if not data["license_number"]:
        m = _LICENSE_LOOSE_RE.search(text.upper())
        if m:
            data["license_number"] = normalize_license(m.group(1))

    addr = _after_label(lines, ["address", "adresse"])
    if addr:
        idx = next((i for i, l in enumerate(lines) if addr in l), None)
        parts = [addr]
        if idx is not None and idx + 1 < len(lines) and config.POSTAL_CODE_RE.search(lines[idx + 1].upper()) \
                and not config.POSTAL_CODE_RE.search(addr.upper()):
            parts.append(lines[idx + 1])
        data["address"] = ", ".join(parts)

    errors.extend(validate_fields(data))
    data["errors"] = errors
    return data


def validate_fields(data):
    """Return a list of validation problems for extracted data."""
    problems = []
    today = date.today()
    dob = parse_date(data.get("date_of_birth"))
    exp = parse_date(data.get("expiry_date"))
    if dob and dob > today:
        problems.append("Date of birth is in the future")
    if exp and dob and exp < dob:
        problems.append("Expiry date is before date of birth")
    if exp and exp < today:
        problems.append("ID is expired")
    lic = data.get("license_number")
    if lic and not validate_license(lic, data.get("province")):
        problems.append(f"License number {lic} does not match expected format")
    return problems


def merge_results(front, back):
    """Merge front/back results, preferring non-empty front values."""
    merged = {f: front.get(f) or back.get(f) for f in FIELDS}
    merged["errors"] = list(dict.fromkeys(front.get("errors", []) + back.get("errors", [])))
    return merged
