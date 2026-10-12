"""Entry point: GUI (default) or CLI for Canadian ID OCR."""
import argparse
import logging
import os
import sys

import config
import data_extractor
import ocr_processor
import pdf_generator
import specimen_generator

logger = logging.getLogger(__name__)


def _save_path(save_dir, src):
    if not save_dir:
        return None
    from urllib.parse import urlparse
    name = os.path.basename(urlparse(src).path) or "image.png"
    if not name.lower().endswith(config.SUPPORTED_EXTENSIONS):
        name += ".png"
    return os.path.join(save_dir, name)


def process_one(front, back=None, edits=None, save_dir=None):
    """OCR a front (and optional back) image/URL and return the merged data."""
    def run(src):
        return data_extractor.extract_fields(
            ocr_processor.process_source(src, edits, _save_path(save_dir, src)))
    result = run(front)
    if back:
        result = data_extractor.merge_results(result, run(back))
    return result


def process_batch(sources, edits=None, save_dir=None):
    """Process many sources; failures are logged and returned as error entries."""
    results = []
    for src in sources:
        try:
            data = process_one(src, edits=edits, save_dir=save_dir)
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


def review_fields(data):
    """Show a dialog to correct extracted fields; returns the corrected data."""
    import tkinter as tk

    win = tk.Tk()
    win.title("Review extracted fields")
    entries = {}
    for i, f in enumerate(data_extractor.FIELDS):
        tk.Label(win, text=f).grid(row=i, column=0, sticky="w", padx=6, pady=2)
        e = tk.Entry(win, width=50)
        e.insert(0, data.get(f) or "")
        e.grid(row=i, column=1, padx=6, pady=2)
        entries[f] = e
    tk.Button(win, text="Done", command=win.quit).grid(row=len(entries), column=1, sticky="e", pady=6)
    win.mainloop()
    fixed = {f: (e.get().strip() or None) for f, e in entries.items()}
    win.destroy()
    fixed["errors"] = data_extractor.validate_fields(fixed)
    return fixed


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
    root.destroy()
    results = [(src, review_fields(data)) for src, data in results]
    root = tk.Tk()
    root.withdraw()
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
    parser.add_argument("--save-images", metavar="DIR", help="save downloaded/edited images to DIR")
    parser.add_argument("--rotate", type=float, default=0, help="rotate clockwise by degrees")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("L", "T", "R", "B"), help="crop box in pixels")
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--make-specimen", metavar="PATH", help="write a SPECIMEN-marked fake test card and exit")
    parser.add_argument("--review", action="store_true", help="review/correct extracted fields in a window before reporting")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    config.setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    if args.make_specimen:
        print(specimen_generator.generate_specimen(args.make_specimen))
        return 0

    if not args.inputs:
        try:
            return run_gui()
        except Exception:
            logger.exception("GUI failed")
            return 1

    edits = {"rotate": args.rotate, "crop": tuple(args.crop) if args.crop else None,
             "brightness": args.brightness, "contrast": args.contrast}
    sources = collect_sources(args.inputs)
    if args.back and len(sources) == 1:
        try:
            results = [(sources[0], process_one(sources[0], args.back, edits, args.save_images))]
        except ocr_processor.OCRError as exc:
            logger.error("%s", exc)
            return 1
    else:
        results = process_batch(sources, edits, args.save_images)
    if args.review:
        results = [(src, review_fields(data)) for src, data in results]
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
