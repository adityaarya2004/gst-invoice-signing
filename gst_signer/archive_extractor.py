"""Extract PDF invoices from nested ZIP/RAR uploads."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

try:
    import rarfile
except ImportError:  # pragma: no cover
    rarfile = None  # type: ignore[assignment,misc]

PDF_MAGIC = b"%PDF"
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
RAR_MAGIC = (b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")

ARCHIVE_SUFFIXES = {".zip", ".rar"}
SKIP_NAMES = {"__MACOSX", ".DS_Store"}


def is_pdf(data: bytes) -> bool:
    return data.startswith(PDF_MAGIC)


def is_zip(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in ZIP_MAGIC)


def is_rar(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in RAR_MAGIC)


def _should_skip(name: str) -> bool:
    parts = Path(name).parts
    return any(part in SKIP_NAMES or part.startswith("._") for part in parts)


def _archive_hint(name: str) -> str:
    """Use archive or PDF basename as AMC naming hint."""
    stem = Path(name).stem
    if stem.endswith(".zip") or stem.endswith(".rar"):
        return Path(stem).stem
    return stem


def _read_zip_entries(data: bytes) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir() or _should_skip(info.filename):
                continue
            entries.append((info.filename, archive.read(info.filename)))
    return entries


def _read_rar_entries(data: bytes) -> list[tuple[str, bytes]]:
    if rarfile is None:
        raise ValueError(
            "RAR support is not installed. Run: pip install rarfile "
            "(and install unrar: brew install unrar on macOS)."
        )

    entries: list[tuple[str, bytes]] = []
    with rarfile.RarFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir() or _should_skip(info.filename):
                continue
            entries.append((info.filename, archive.read(info)))
    return entries


def _collect_pdfs(data: bytes, source_name: str = "") -> list[tuple[str, bytes]]:
    """Recursively collect PDFs from PDF/ZIP/RAR byte payloads."""
    if is_pdf(data):
        hint = _archive_hint(source_name) if source_name else "invoice"
        return [(hint, data)]

    if is_zip(data):
        pdfs: list[tuple[str, bytes]] = []
        for name, content in _read_zip_entries(data):
            basename = Path(name).name
            if is_pdf(content):
                pdfs.append((_archive_hint(name), content))
            elif is_zip(content) or is_rar(content):
                pdfs.extend(_collect_pdfs(content, basename))
            elif Path(name).suffix.lower() in ARCHIVE_SUFFIXES:
                pdfs.extend(_collect_pdfs(content, basename))
        return pdfs

    if is_rar(data):
        pdfs = []
        for name, content in _read_rar_entries(data):
            basename = Path(name).name
            if is_pdf(content):
                pdfs.append((_archive_hint(name), content))
            elif is_zip(content) or is_rar(content):
                pdfs.extend(_collect_pdfs(content, basename))
            elif Path(name).suffix.lower() in ARCHIVE_SUFFIXES:
                pdfs.extend(_collect_pdfs(content, basename))
        return pdfs

    raise ValueError("Unsupported file format")


def extract_pdfs_from_upload(
    data: bytes,
    source_label: str = "upload",
) -> list[tuple[str, bytes]]:
    """
    Extract invoice PDFs from a PDF or nested ZIP/RAR upload.

    Supports:
    - Combined PDF (legacy)
    - Outer ZIP/RAR with per-company nested ZIP/RAR files containing PDFs
    - Single company ZIP/RAR containing a PDF
    """
    try:
        pdfs = _collect_pdfs(data)
    except ValueError as exc:
        if "Unsupported" in str(exc):
            raise ValueError(
                f"Unsupported {source_label} upload. Expected a PDF, ZIP, or RAR file "
                "containing invoice PDFs."
            ) from exc
        raise

    if not pdfs:
        raise ValueError(
            f"No PDF invoices found in the {source_label} upload. "
            "Check that archives contain GST invoice PDF files."
        )
    return pdfs


def extract_pdfs_from_kfin_upload(data: bytes) -> list[tuple[str, bytes]]:
    """Extract invoice PDFs from a KFintech upload."""
    return extract_pdfs_from_upload(data, source_label="KFintech")


def extract_pdfs_from_cams_upload(data: bytes) -> list[tuple[str, bytes]]:
    """Extract invoice PDFs from a CAMS upload."""
    return extract_pdfs_from_upload(data, source_label="CAMS")
