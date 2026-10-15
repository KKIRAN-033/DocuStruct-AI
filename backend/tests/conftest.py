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


# ─── Phase 2 Synthetic Fixtures ──────────────────────────────────────────


@pytest.fixture
def synthetic_empty_page_pdf(tmp_path: Path) -> Path:
    """Create a 1-page PDF with no text, no images, and no drawings."""
    pdf_path = tmp_path / "synthetic_empty.pdf"
    doc = pymupdf.open()
    try:
        doc.new_page(width=595, height=842)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_scanned_pdf(tmp_path: Path) -> Path:
    """Create a 1-page PDF with an image covering >60% and 0 printable text."""
    pdf_path = tmp_path / "synthetic_scanned.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=500, height=500)
        # 400x400 image on 500x500 page = 64% coverage
        pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 50, 50), False)
        page.insert_image(pymupdf.Rect(50, 50, 450, 450), pixmap=pix)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_hybrid_pdf(tmp_path: Path) -> Path:
    """Create a 1-page PDF with native text (>=50 chars) and ~25% image coverage."""
    pdf_path = tmp_path / "synthetic_hybrid.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=500, height=500)
        page.insert_text(
            (50, 40),
            "This is native digital text that exceeds fifty characters in total length for hybrid page testing.",
            fontsize=10,
        )
        # 250x250 image on 500x500 page = 25% coverage
        pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 50, 50), False)
        page.insert_image(pymupdf.Rect(50, 100, 300, 350), pixmap=pix)
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_nontable_pdf(tmp_path: Path) -> Path:
    """Create a 1-page digital PDF with paragraphs but no tables or aligned columns."""
    pdf_path = tmp_path / "synthetic_nontable.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=595, height=842)
        paragraphs = [
            "DocuStruct AI is an enterprise document extraction framework designed for accuracy.",
            "This document is a regular narrative report describing general project updates.",
            "It contains normal sentence structure, flowing text paragraphs, and no tabular layout.",
            "Financial results are discussed qualitatively in prose rather than via tables.",
        ]
        y = 72
        for p in paragraphs:
            page.insert_text((72, y), p, fontsize=10)
            y += 40
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_ruled_table_pdf(tmp_path: Path) -> Path:
    """Create a 1-page digital PDF with drawn grid lines and cell text in grid intersections."""
    pdf_path = tmp_path / "synthetic_ruled_table.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=612, height=792)
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols, rows = 3, 3

        # Draw grid lines
        for r in range(rows + 1):
            y = y_start + r * row_h
            page.draw_line(
                pymupdf.Point(x_start, y),
                pymupdf.Point(x_start + cols * col_w, y),
            )
        for c in range(cols + 1):
            x = x_start + c * col_w
            page.draw_line(
                pymupdf.Point(x, y_start),
                pymupdf.Point(x, y_start + rows * row_h),
            )

        # Insert cell text
        data = [
            ["Account", "Amount", "Status"],
            ["0012345", "1,234.56", "Active"],
            ["0067890", "(450.50)", "Pending"],
        ]
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                x = x_start + c * col_w + 10
                y = y_start + r * row_h + 20
                page.insert_text((x, y), cell, fontsize=9)

        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_borderless_table_pdf(tmp_path: Path) -> Path:
    """Create a 1-page digital PDF with coordinate-aligned columns and rows but zero vector lines."""
    pdf_path = tmp_path / "synthetic_borderless_table.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=612, height=792)
        rows = [
            ("Invoice No", "Description", "Total Amount"),
            ("00101", "Software License", "1,500.00"),
            ("00102", "Consulting Services", "2,350.50"),
            ("00103", "Support Package", "450.00-"),
        ]
        y = 100
        for row in rows:
            page.insert_text((50, y), row[0], fontsize=10)
            page.insert_text((200, y), row[1], fontsize=10)
            page.insert_text((420, y), row[2], fontsize=10)
            y += 25
        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_multipage_continuation_pdf(tmp_path: Path) -> Path:
    """Create a 2-page digital PDF with a ruled table that continues across pages with repeated headers."""
    pdf_path = tmp_path / "synthetic_multipage_continuation.pdf"
    doc = pymupdf.open()
    try:
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols = 3

        # Page 1: 4 rows (1 header + 3 data)
        p1 = doc.new_page(width=612, height=792)
        rows_p1 = 4
        for r in range(rows_p1 + 1):
            y = y_start + r * row_h
            p1.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
        for c in range(cols + 1):
            x = x_start + c * col_w
            p1.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows_p1 * row_h))

        data_p1 = [
            ["Item", "Amount", "Status"],
            ["Item 1", "100.00", "Active"],
            ["Item 2", "200.00", "Active"],
            ["Item 3", "300.00", "Active"],
        ]
        for r, row in enumerate(data_p1):
            for c, cell in enumerate(row):
                p1.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)

        # Page 2: 5 rows (1 repeated header + 3 data + 1 total)
        p2 = doc.new_page(width=612, height=792)
        rows_p2 = 5
        for r in range(rows_p2 + 1):
            y = y_start + r * row_h
            p2.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
        for c in range(cols + 1):
            x = x_start + c * col_w
            p2.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows_p2 * row_h))

        data_p2 = [
            ["Item", "Amount", "Status"],
            ["Item 4", "400.00", "Active"],
            ["Item 5", "500.00", "Active"],
            ["Item 6", "600.00", "Active"],
            ["Total", "2,100.00", "Completed"],
        ]
        for r, row in enumerate(data_p2):
            for c, cell in enumerate(row):
                p2.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)

        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_duplicate_rows_pdf(tmp_path: Path) -> Path:
    """Create a 1-page digital PDF with genuine duplicate transaction rows."""
    pdf_path = tmp_path / "synthetic_duplicate_rows.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=612, height=792)
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols, rows = 3, 4

        for r in range(rows + 1):
            y = y_start + r * row_h
            page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
        for c in range(cols + 1):
            x = x_start + c * col_w
            page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

        data = [
            ["TxID", "Description", "Amount"],
            ["TX-901", "Monthly Fee", "49.99"],
            ["TX-901", "Monthly Fee", "49.99"],  # Duplicate row
            ["TX-902", "Setup Fee", "150.00"],
        ]
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                page.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)

        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path


@pytest.fixture
def synthetic_arithmetic_discrepancy_pdf(tmp_path: Path) -> Path:
    """Create a 1-page digital PDF with a ruled table having a printed total arithmetic mismatch."""
    pdf_path = tmp_path / "synthetic_arithmetic_discrepancy.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=612, height=792)
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols, rows = 3, 4

        for r in range(rows + 1):
            y = y_start + r * row_h
            page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
        for c in range(cols + 1):
            x = x_start + c * col_w
            page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

        data = [
            ["Item", "Amount", "Status"],
            ["Alpha", "100.00", "Valid"],
            ["Beta", "200.00", "Valid"],
            ["Total", "350.00", "Discrepancy"],  # Printed 350.00 != computed 300.00
        ]
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                page.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)

        doc.save(str(pdf_path))
    finally:
        doc.close()
    return pdf_path

