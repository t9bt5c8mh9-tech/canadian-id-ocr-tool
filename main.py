"""Entry point: GUI (default) or CLI for Canadian ID OCR."""
import argparse
import logging
import os
import sys

import config
import data_extractor
import ocr_processor
import pdf_generator

logger = logging.getLogger(__name__)


def process_one(front, back=None):
    """OCR a front (and optional back) image/URL and return the merged data."""
    result = data_extractor.extract_fields(ocr_processor.process_source(front))
    if back:
        result = data_extractor.merge_results(result, data_extractor.extract_fields(ocr_processor.process_source(back)))
    return result


def process_batch(sources):
    """Process many sources; failures are logged and returned as error entries."""
    results = []
    for src in sources:
        try:
            data = process_one(src)
        except ocr_processor.OCRError as exc:
            logger.error("Failed %s: %s", src, exc)
            data = {f: None for f in data_extractor.FIELDS}
            data["errors"] = [str(exc)]
        results.append((src, data))
    return results


def collect_sources(paths):
    """Expand directories into supported image files."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            out.extend(os.path.join(p, f) for f in sorted(os.listdir(p))
                       if f.lower().endswith(config.SUPPORTED_EXTENSIONS))
        else:
            out.append(p)
    return out


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog

    root = tk.Tk()
    root.withdraw()
    patterns = " ".join("*" + e for e in config.SUPPORTED_EXTENSIONS)
    files = filedialog.askopenfilenames(title="Select ID image(s) (front and/or back)",
                                        filetypes=[("Images", patterns)])
    if not files:
        return 0
    results = process_batch(files)
    if len(files) == 2:
        merged = data_extractor.merge_results(results[0][1], results[1][1])
        results = [(" + ".join(files), merged)]
    out = filedialog.asksaveasfilename(title="Save PDF report", defaultextension=".pdf",
                                       filetypes=[("PDF", "*.pdf")])
    if out:
        pdf_generator.generate_report(results, out)
        messagebox.showinfo("Done", f"Report saved to {out}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract data from Canadian driver's licences / ID cards")
    parser.add_argument("inputs", nargs="*", help="image files, directories or URLs (omit for GUI)")
    parser.add_argument("-o", "--output", help="PDF report path")
    parser.add_argument("--back", help="back-of-card image (single input only)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    config.setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    if not args.inputs:
        try:
            return run_gui()
        except Exception:
            logger.exception("GUI failed")
            return 1

    sources = collect_sources(args.inputs)
    if args.back and len(sources) == 1:
        try:
            results = [(sources[0], process_one(sources[0], args.back))]
        except ocr_processor.OCRError as exc:
            logger.error("%s", exc)
            return 1
    else:
        results = process_batch(sources)
    for src, data in results:
        print(src)
        for f in data_extractor.FIELDS:
            print(f"  {f}: {data.get(f)}")
        for e in data.get("errors", []):
            print(f"  ! {e}")
    if args.output:
        pdf_generator.generate_report(results, args.output)
    return 0 if all(not d.get("errors") or any(d.get(f) for f in data_extractor.FIELDS) for _, d in results) else 1


if __name__ == "__main__":
    sys.exit(main())
