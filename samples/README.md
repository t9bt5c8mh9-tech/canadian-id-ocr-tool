# Reference licence templates

Realistic card images downloaded from the internet, used as visual/size
reference for `specimen_generator.py` and for OCR smoke tests.

| File | Side | Source |
|------|------|--------|
| `ontario_sample_front.png` | front | Locally rendered Ontario-style SPECIMEN card (fake data) — layout mirrors a real Ontario licence per public ontario.ca / AGCO references |
| `ontario_sample_back.png` | back | Locally rendered: PDF417-style barcode + trillium number + back fields |
| `license_front_reference_1.jpg` | front | District of Columbia "SAMPLE CARD" (Thomas Alexander) |
| `license_front_reference_2.jpg` | front | New York State "SAMPLE" (Michael M Sample) |
| `license_back_reference.png` | back | Generated locally: PDF417-style barcode + typical back fields |

The two `license_front_reference_*.jpg` files are official government-issued
**sample** images (fake "SAMPLE" data) collected in the public
[`lucky-verma/US-Driver-License-data-extraction`](https://github.com/lucky-verma/US-Driver-License-data-extraction)
dataset (`DATASET/DL America/licenses/`, scraped from the internet).

The `ontario_sample_*.png` files are **locally rendered** fake SPECIMEN cards
whose field layout (photo left; Name / Licence No / Date of Birth / Expiry /
Address / Class on the right; barcode + trillium number on the back) mirrors a
real Ontario driver's licence, based on public ontario.ca / AGCO reference
material. They contain only fabricated data and are permanently stamped
"SPECIMEN".

**Legal note:** official licence artwork is not publicly distributed, and
reproducing a printable licence is illegal. These fixtures are for OCR testing
only and are not printable IDs. No real person's personal ID image is stored in
this repository.

`ontario_specimen.png` is the earlier locally generated SPECIMEN card (fake data).
