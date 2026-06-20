# GST Invoice Signing Tool

A Python desktop application for signing Mutual Fund distributor GST invoices. Upload combined CAMS and KFintech PDF files, add your signature image, and download a ZIP of individually signed AMC invoices.

## Features

- Processes combined CAMS and KFintech/Karvy invoice PDFs
- Supports two invoice formats:
  - **Format A (CAMS/KFintech):** Inserts signature between `For Narendra Kumar Arya` and `Authorised Signatory`
  - **Format B (Nippon style):** Fills signatory fields and places signature above the `Signature` label
- Extracts AMC names automatically for output filenames
- Preserves original PDF quality (no rasterization)
- Generates `signed_invoices.zip` with one PDF per AMC

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## Quick Start

```bash
make install
make gst
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

## Usage

1. Upload **CAMS PDF** (optional if only KFintech invoices)
2. Upload **KFintech PDF** (optional if only CAMS invoices)
3. Upload **Signature PNG**
4. Click **Generate Signed Invoices**
5. Download **signed_invoices.zip**

## Output Structure

```
signed_invoices.zip
├── DSP Mutual Fund.pdf
├── HDFC Mutual Fund.pdf
├── SBI Mutual Fund.pdf
├── Nippon India Mutual Fund.pdf
└── ...
```

## Project Structure

```
gst-invoice-signing/
├── app.py                 # Streamlit UI
├── gst_signer/
│   ├── __init__.py
│   └── processor.py       # PDF processing functions
├── requirements.txt
├── Makefile
└── README.md
```

## Processing Functions

| Function | Description |
|---|---|
| `detect_format()` | Detects Format A or Format B from page text |
| `extract_amc_name()` | Extracts AMC name for output filename |
| `add_signature_format_a()` | Signs CAMS/KFintech style invoices |
| `add_signature_format_b()` | Signs Nippon-style invoices |
| `split_pdf_pages()` | Splits combined PDF into single pages |
| `create_zip()` | Packages signed PDFs into a ZIP file |
| `process_cams_pdf()` | Processes CAMS combined PDF |
| `process_kfin_pdf()` | Processes KFintech combined PDF |

## Technology

- Python
- Streamlit
- PyMuPDF (fitz)
- zipfile
- re
- pathlib

## Notes

- Original PDF text remains selectable; pages are not converted to images.
- If duplicate AMC names appear across uploads, filenames are deduplicated with `(2)`, `(3)`, etc.
- At least one PDF and a signature PNG are required to generate output.
