"""Core PDF processing logic for GST invoice signing."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Callable, Literal

import fitz

from gst_signer.archive_extractor import extract_pdfs_from_cams_upload, extract_pdfs_from_kfin_upload, is_pdf

FormatType = Literal["format_a", "format_b"]

SIGNATORY_NAME = "Narendra Kumar Arya"

FORMAT_A_NAME_MARKER = "For Narendra Kumar Arya"
FORMAT_A_SIGNATORY_LABEL = "Authorised Signatory"

FORMAT_B_MARKERS = (
    "Name of the Signatory",
    "Designation / Status",
    "Signature",
)

KNOWN_AMC_NAMES = [
    "Aditya Birla Sun Life Mutual Fund",
    "ICICI Prudential Mutual Fund",
    "Franklin Templeton Mutual Fund",
    "Nippon India Mutual Fund",
    "DSP Mutual Fund",
    "HDFC Mutual Fund",
    "SBI Mutual Fund",
    "HSBC Mutual Fund",
    "Tata Mutual Fund",
    "Mirae Asset Mutual Fund",
    "Axis Mutual Fund",
    "Kotak Mahindra Mutual Fund",
    "Invesco Mutual Fund",
    "PGIM India Mutual Fund",
    "Quant Mutual Fund",
    "Bandhan Mutual Fund",
    "Edelweiss Mutual Fund",
    "Motilal Oswal Mutual Fund",
    "Union Mutual Fund",
    "Mahindra Manulife Mutual Fund",
    "Baroda BNP Paribas Mutual Fund",
    "Canara Robeco Mutual Fund",
    "LIC Mutual Fund",
    "ITI Mutual Fund",
    "JM Financial Mutual Fund",
    "WhiteOak Capital Mutual Fund",
    "Samco Mutual Fund",
    "Trust Mutual Fund",
    "Shriram Mutual Fund",
    "Groww Mutual Fund",
    "Zerodha Mutual Fund",
    "Bajaj Finserv Mutual Fund",
    "Sundaram Mutual Fund",
    "UTI Mutual Fund",
]

KFIN_ARCHIVE_NAME_MAP = {
    "AXIS": "Axis Mutual Fund",
    "BAJAJ": "Bajaj Finserv Mutual Fund",
    "INVESCO": "Invesco Mutual Fund",
    "MIRAE": "Mirae Asset Mutual Fund",
    "MOTILAL": "Motilal Oswal Mutual Fund",
    "NIMF": "Nippon India Mutual Fund",
    "SUNDARAM": "Sundaram Mutual Fund",
    "UTI": "UTI Mutual Fund",
}

AMC_REGEX = re.compile(
    r"([A-Za-z0-9&\.\-'\s]+?\sMutual Fund)",
    re.IGNORECASE,
)

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

MANIFEST_FILENAME = "signed_files.txt"
CAMS_ZIP_FILENAME = "cams_signed.zip"
KFIN_ZIP_FILENAME = "kfin_signed.zip"


def amc_name_from_archive_hint(hint: str) -> str | None:
    """Map KFintech archive filename prefix to a known AMC name."""
    prefix = re.split(r"[_\-\s]", hint, maxsplit=1)[0].strip()
    if not prefix:
        return None

    mapped = KFIN_ARCHIVE_NAME_MAP.get(prefix.upper())
    if mapped:
        return mapped

    for amc in KNOWN_AMC_NAMES:
        if prefix.lower() in amc.lower():
            return amc

    return None


def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in filenames."""
    cleaned = INVALID_FILENAME_CHARS.sub("", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "Unknown AMC"


def make_short_filename(amc_name: str) -> str:
    """Build PDF filename from the first word of the AMC name (e.g. Franklin.pdf)."""
    parts = amc_name.strip().split()
    first_word = parts[0] if parts else "Unknown"
    return f"{sanitize_filename(first_word)}.pdf"


def unique_pdf_filename(filename: str, existing: dict[str, bytes]) -> str:
    """Ensure filename is unique using Franklin2.pdf style suffixes (no spaces)."""
    if filename not in existing:
        return filename

    stem = Path(filename).stem
    counter = 2
    while True:
        candidate = f"{stem}{counter}.pdf"
        if candidate not in existing:
            return candidate
        counter += 1


def build_file_manifest(cams_files: list[str], kfin_files: list[str]) -> str:
    """Build a text manifest listing CAMS and KFintech output PDF names."""
    lines = [f"CAMS Files (in {CAMS_ZIP_FILENAME}):"]
    if cams_files:
        lines.extend(sorted(cams_files))
    else:
        lines.append("(none)")

    lines.append("")
    lines.append(f"KFintech Files (in {KFIN_ZIP_FILENAME}):")
    if kfin_files:
        lines.extend(sorted(kfin_files))
    else:
        lines.append("(none)")

    return "\n".join(lines) + "\n"


def detect_format(page: fitz.Page) -> FormatType:
    """Detect invoice layout from page text."""
    text = page.get_text("text")
    normalized = " ".join(text.split())

    if all(marker in normalized for marker in FORMAT_B_MARKERS):
        return "format_b"

    if FORMAT_A_NAME_MARKER in normalized and FORMAT_A_SIGNATORY_LABEL in normalized:
        return "format_a"

    if "Name of the Signatory" in normalized and "Signature" in normalized:
        return "format_b"

    if FORMAT_A_SIGNATORY_LABEL in normalized:
        return "format_a"

    return "format_a"


def extract_amc_name(page: fitz.Page) -> str:
    """Extract AMC name from invoice page text."""
    text = page.get_text("text")

    for amc in KNOWN_AMC_NAMES:
        if amc.lower() in text.lower():
            return amc

    matches = AMC_REGEX.findall(text)
    if matches:
        best = max(matches, key=len)
        return sanitize_filename(best.title())

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if "mutual fund" in line.lower():
            return sanitize_filename(line)

    return "Unknown AMC"


def _find_text_rect(page: fitz.Page, text: str) -> fitz.Rect | None:
    """Return the first bounding box for exact text match."""
    rects = page.search_for(text)
    return rects[0] if rects else None


def _find_text_rect_fuzzy(page: fitz.Page, text: str) -> fitz.Rect | None:
    """Find text rect using exact search, then case-insensitive block scan."""
    rect = _find_text_rect(page, text)
    if rect is not None:
        return rect

    needle = text.lower()
    blocks = page.get_text("blocks")
    for block in blocks:
        if len(block) < 5:
            continue
        block_text = str(block[4]).strip()
        if needle in block_text.lower():
            return fitz.Rect(block[:4])

    return None


def _find_format_a_name_line(page: fitz.Page) -> fitz.Rect | None:
    """Locate the 'For Narendra Kumar Arya' line (case-insensitive)."""
    direct = _find_text_rect_fuzzy(page, FORMAT_A_NAME_MARKER)
    if direct is not None:
        return direct

    pattern = re.compile(r"for\s+narendra\s+kumar\s+arya", re.IGNORECASE)
    for block in page.get_text("blocks"):
        if len(block) < 5:
            continue
        block_text = str(block[4]).strip()
        if pattern.search(block_text):
            return fitz.Rect(block[:4])

    return None


def _insert_text_above_label(
    page: fitz.Page,
    label: str,
    value: str,
    font_size: float = 10.0,
    offset: float = 12.0,
) -> bool:
    """Insert value text above a label field."""
    rect = _find_text_rect_fuzzy(page, label)
    if rect is None:
        return False

    page.insert_text(
        fitz.Point(rect.x0, rect.y0 - offset),
        value,
        fontsize=font_size,
        fontname="helv",
        color=(0, 0, 0),
    )
    return True


def _signatory_name_present(page: fitz.Page, signatory_name: str, name_label: fitz.Rect) -> bool:
    """Check if signatory name already appears above the signatory block."""
    region = fitz.Rect(
        name_label.x0 - 20,
        name_label.y0 - 24,
        name_label.x1 + 120,
        name_label.y0 + 2,
    )
    text = page.get_text("text", clip=region)
    return signatory_name.strip().lower() in text.lower()


def add_signature_format_b(
    page: fitz.Page,
    signature_bytes: bytes,
    signatory_name: str,
) -> None:
    """
    KFintech layout: place signatory name above 'Name of the Signatory',
    leave 'Designation / Status' blank, and insert signature above 'Signature'.
    """
    name_label = _find_text_rect_fuzzy(page, "Name of the Signatory")
    designation_rect = _find_text_rect_fuzzy(page, "Designation / Status")
    signature_label = _find_text_rect_fuzzy(page, "Signature")

    if signature_label is None:
        raise ValueError("Could not locate 'Signature' field on page.")

    cleaned_name = signatory_name.strip()
    if cleaned_name and name_label and not _signatory_name_present(page, cleaned_name, name_label):
        _insert_text_above_label(page, "Name of the Signatory", cleaned_name)

    if designation_rect:
        gap_top = designation_rect.y1 + 4
    elif name_label:
        gap_top = name_label.y1 + 8
    else:
        gap_top = signature_label.y0 - 48

    gap_bottom = signature_label.y0 - 4
    available_height = max(gap_bottom - gap_top, 20)

    signature_height = min(42.0, available_height)
    signature_width = min(130.0, page.rect.width * 0.25)

    anchor = name_label or signature_label
    x0 = anchor.x0
    y0 = gap_top
    img_rect = fitz.Rect(x0, y0, x0 + signature_width, y0 + signature_height)

    page.insert_image(img_rect, stream=signature_bytes, keep_proportion=True)


def add_signature_format_a(page: fitz.Page, signature_bytes: bytes) -> None:
    """
    Insert signature between 'For Narendra Kumar Arya' and
    'Authorised Signatory'.
    """
    name_rect = _find_format_a_name_line(page)
    signatory_rect = _find_text_rect_fuzzy(page, FORMAT_A_SIGNATORY_LABEL)

    if name_rect is None or signatory_rect is None:
        raise ValueError(
            f"Could not locate '{FORMAT_A_NAME_MARKER}' and "
            f"'{FORMAT_A_SIGNATORY_LABEL}' on page."
        )

    gap_top = name_rect.y1 + 3
    gap_bottom = signatory_rect.y0 - 3
    available_height = max(gap_bottom - gap_top, 20)

    signature_height = min(42.0, available_height)
    signature_width = min(130.0, page.rect.width * 0.28)

    x0 = name_rect.x0
    y0 = gap_top
    img_rect = fitz.Rect(x0, y0, x0 + signature_width, y0 + signature_height)

    page.insert_image(img_rect, stream=signature_bytes, keep_proportion=True)


def split_pdf_pages(pdf_bytes: bytes) -> list[tuple[int, fitz.Document]]:
    """Split a multi-page PDF into single-page documents."""
    source = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[tuple[int, fitz.Document]] = []

    for page_index in range(source.page_count):
        single = fitz.open()
        single.insert_pdf(source, from_page=page_index, to_page=page_index)
        pages.append((page_index, single))

    source.close()
    return pages


def _process_single_page(
    page_doc: fitz.Document,
    signature_bytes: bytes,
    log: Callable[[str], None],
    name_hint: str | None = None,
    signatory_name: str = "",
) -> tuple[str, bytes]:
    """Apply signature to one page and return AMC filename + PDF bytes."""
    page = page_doc[0]
    invoice_format = detect_format(page)
    amc_name = extract_amc_name(page)

    if amc_name == "Unknown AMC" and name_hint:
        hinted = amc_name_from_archive_hint(name_hint)
        if hinted:
            amc_name = hinted
            log(f"Using AMC name from archive: {amc_name}")
        else:
            amc_name = sanitize_filename(name_hint.split("_")[0]) + " Mutual Fund"

    log(f"Processing {amc_name}")

    if invoice_format == "format_b":
        if not signatory_name.strip():
            raise ValueError("Signatory name is required for KFintech invoices.")
        add_signature_format_b(page, signature_bytes, signatory_name)
    else:
        add_signature_format_a(page, signature_bytes)

    log("Signature Added")

    pdf_bytes = page_doc.tobytes(garbage=4, deflate=True)
    filename = make_short_filename(amc_name)
    log(f"Saved PDF: {filename}")

    page_doc.close()
    return filename, pdf_bytes


def _process_pdf_bytes(
    pdf_bytes: bytes,
    signature_bytes: bytes,
    log: Callable[[str], None],
    name_hint: str | None = None,
    signatory_name: str = "",
) -> dict[str, bytes]:
    """Process all pages in a combined PDF."""
    signed_files: dict[str, bytes] = {}
    split_pages = split_pdf_pages(pdf_bytes)

    for _, page_doc in split_pages:
        filename, signed_pdf = _process_single_page(
            page_doc,
            signature_bytes,
            log,
            name_hint=name_hint,
            signatory_name=signatory_name,
        )

        filename = unique_pdf_filename(filename, signed_files)
        signed_files[filename] = signed_pdf

    return signed_files


def _process_archived_upload(
    file_bytes: bytes,
    signature_bytes: bytes,
    log: Callable[[str], None],
    extract_pdfs: Callable[[bytes], list[tuple[str, bytes]]],
    signatory_name: str = "",
) -> dict[str, bytes]:
    """Process a combined PDF or nested ZIP/RAR invoice upload."""
    if is_pdf(file_bytes):
        return _process_pdf_bytes(
            file_bytes,
            signature_bytes,
            log,
            signatory_name=signatory_name,
        )

    signed_files: dict[str, bytes] = {}
    pdf_entries = extract_pdfs(file_bytes)

    for name_hint, pdf_bytes in pdf_entries:
        log(f"Found invoice PDF: {name_hint}")
        company_signed = _process_pdf_bytes(
            pdf_bytes,
            signature_bytes,
            log,
            name_hint=name_hint,
            signatory_name=signatory_name,
        )
        for filename, content in company_signed.items():
            filename = unique_pdf_filename(filename, signed_files)
            signed_files[filename] = content

    return signed_files


def process_cams_pdf(
    file_bytes: bytes,
    signature_bytes: bytes,
    log: Callable[[str], None] | None = None,
) -> dict[str, bytes]:
    """
    Process CAMS uploads.

    Accepts a combined PDF or a nested ZIP/RAR bundle where each company
    archive contains one or more invoice PDFs.
    """
    logger = log or (lambda _msg: None)
    return _process_archived_upload(
        file_bytes,
        signature_bytes,
        logger,
        extract_pdfs_from_cams_upload,
    )


def process_kfin_pdf(
    file_bytes: bytes,
    signature_bytes: bytes,
    log: Callable[[str], None] | None = None,
    signatory_name: str = "",
) -> dict[str, bytes]:
    """
    Process KFintech/Karvy uploads.

    Accepts a combined PDF or a nested ZIP/RAR bundle where each company
    archive contains one or more invoice PDFs.
    """
    logger = log or (lambda _msg: None)
    return _process_archived_upload(
        file_bytes,
        signature_bytes,
        logger,
        extract_pdfs_from_kfin_upload,
        signatory_name=signatory_name,
    )


def _create_inner_zip(files: dict[str, bytes]) -> bytes:
    """Create a ZIP archive containing PDF files only."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in sorted(files.items()):
            archive.writestr(filename, content)
    return buffer.getvalue()


def create_zip(
    cams_files: dict[str, bytes] | None = None,
    kfin_files: dict[str, bytes] | None = None,
    cams_names: list[str] | None = None,
    kfin_names: list[str] | None = None,
) -> bytes:
    """
    Create the final download package:
    - cams_signed.zip  (all CAMS signed PDFs)
    - kfin_signed.zip  (all KFintech signed PDFs)
    - signed_files.txt (common manifest listing both)
    """
    cams_pdfs = cams_files or {}
    kfin_pdfs = kfin_files or {}
    cams_list = cams_names or sorted(cams_pdfs.keys())
    kfin_list = kfin_names or sorted(kfin_pdfs.keys())

    if not cams_pdfs and not kfin_pdfs:
        raise ValueError("No signed files to package.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            MANIFEST_FILENAME,
            build_file_manifest(cams_list, kfin_list),
        )

        if cams_pdfs:
            archive.writestr(CAMS_ZIP_FILENAME, _create_inner_zip(cams_pdfs))

        if kfin_pdfs:
            archive.writestr(KFIN_ZIP_FILENAME, _create_inner_zip(kfin_pdfs))

    return buffer.getvalue()
