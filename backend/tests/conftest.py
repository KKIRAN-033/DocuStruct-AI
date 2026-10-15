"""
DocuStruct AI — Test Fixtures

Synthetic PDF fixtures generated using PyMuPDF (fitz) for
reproducible unit testing without external test-data files.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def isolated_test_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test isolation."""
    return tmp_path


@pytest.fixture
def valid_digital_pdf(tmp_path: Path) -> Path:
    """Create a minimal 1-page valid PDF with text content."""
    pdf_path = tmp_path / "valid_digital.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "DocuStruct AI Test Document", fontsize=12)
        page.insert_text((72, 100), "This is a valid digital PDF for testing.", fontsize=10)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def multipage_3_pdf(tmp_path: Path) -> Path:
    """Create a 3-page PDF with text on each page."""
    pdf_path = tmp_path / "multipage_3.pdf"
    doc = pymupdf.open()
    try:
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"Page {i + 1} content", fontsize=12)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def multipage_51_pdf(tmp_path: Path) -> Path:
    """Create a PDF with 51 blank pages (exceeds 50-page limit)."""
    pdf_path = tmp_path / "multipage_51.pdf"
    doc = pymupdf.open()
    try:
        for _ in range(51):
            doc.new_page(width=595, height=842)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def encrypted_pdf(tmp_path: Path) -> Path:
    """Create an encrypted/password-protected PDF."""
    pdf_path = tmp_path / "encrypted.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Secret content", fontsize=12)
        # Save with user password
        doc.save(
            str(pdf_path),
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="testpassword",
            owner_pw="ownerpassword",
        )
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def corrupt_pdf_file(tmp_path: Path) -> Path:
    """Create a file with valid %PDF- header but truncated body."""
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\nGARBAGE CORRUPT DATA")
    return pdf_path


@pytest.fixture
def non_pdf_file(tmp_path: Path) -> Path:
    """Create a plain text file without %PDF- header."""
    txt_path = tmp_path / "not_a_pdf.txt"
    txt_path.write_text("This is not a PDF file.", encoding="utf-8")
    return txt_path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create a zero-byte empty file."""
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(b"")
    return empty_path


@pytest.fixture
def oversized_file(tmp_path: Path) -> Path:
    """Create a file that exceeds 25 MiB with valid %PDF- header.

    We write just over the limit with a valid header prefix.
    """
    big_path = tmp_path / "oversized.pdf"
    size = 26_214_400 + 1024  # Just over 25 MiB
    with open(big_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"\x00" * (size - 9))
    return big_path
