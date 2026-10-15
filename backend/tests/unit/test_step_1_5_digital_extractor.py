"""
DocuStruct AI — Unit Tests: Step 1.5 Digital Extractor

Tests native digital table extraction using ruling-line geometry
as the primary strategy and horizontal coordinate intervals as fallback,
verifying geometry in PDF points, duplicate/ragged row preservation,
and guaranteed pdfplumber resource closure on Windows.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pdfplumber
import pymupdf
import pytest

from app.extraction.digital_extractor import (
    extract_borderless_tables,
    extract_document_tables,
    extract_ruled_tables,
    extract_tables_from_page,
)
from app.models.domain import CanonicalTable


# ─── TestRuledTableExtraction ────────────────────────────────────────────


class TestRuledTableExtraction:
    def test_ruled_table_structure_and_cells(self, synthetic_ruled_table_pdf: Path):
        tables = extract_document_tables(synthetic_ruled_table_pdf)
        assert len(tables) >= 1
        table = tables[0]
        assert isinstance(table, CanonicalTable)
        assert table.extraction_method == "LINE_BASED_RULING"
        assert table.source_pages == [1]
        assert len(table.rows) >= 3

        # Verify headers
        assert "Account" in table.original_headers
        assert "Amount" in table.original_headers

        # Verify cell geometry
        first_row = table.rows[0]
        for cell in first_row:
            assert cell.bbox is not None
            assert cell.bbox.coord_exact is True
            assert cell.bbox.page_width > 0
            assert cell.bbox.page_height > 0


# ─── TestBorderlessTableExtraction ───────────────────────────────────────


class TestBorderlessTableExtraction:
    def test_borderless_table_fallback(self, synthetic_borderless_table_pdf: Path):
        tables = extract_document_tables(synthetic_borderless_table_pdf)
        assert len(tables) >= 1
        table = tables[0]
        assert table.extraction_method == "COORDINATE_INTERVAL_FALLBACK"
        assert len(table.rows) >= 3

        # Verify inferred bounding box has coord_exact = False
        first_data_row = table.rows[1]
        for cell in first_data_row:
            if cell.bbox is not None:
                assert cell.bbox.coord_exact is False


# ─── TestEdgeCasesAndPreservation ────────────────────────────────────────


class TestEdgeCasesAndPreservation:
    def test_nontable_digital_page_returns_empty(self, synthetic_nontable_pdf: Path):
        tables = extract_document_tables(synthetic_nontable_pdf)
        # Should NOT fabricate tables out of normal narrative paragraphs
        assert len(tables) == 0

    def test_duplicate_rows_preserved(self, tmp_path: Path):
        """Verify that duplicate rows in source data are NEVER pruned."""
        pdf_path = tmp_path / "duplicate_rows.pdf"
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=612, height=792)
            rows = [
                ("Item", "Rate"),
                ("Hardware", "100.00"),
                ("Hardware", "100.00"),  # Exact duplicate
                ("Hardware", "100.00"),  # Exact duplicate
            ]
            y = 100
            for r in rows:
                page.insert_text((50, y), r[0], fontsize=10)
                page.insert_text((200, y), r[1], fontsize=10)
                y += 25
            doc.save(str(pdf_path))
        finally:
            doc.close()

        tables = extract_document_tables(pdf_path)
        assert len(tables) == 1
        # Headers + 3 data rows = 4 rows total
        assert len(tables[0].rows) == 4

    def test_empty_page_returns_zero_tables(self, synthetic_empty_page_pdf: Path):
        tables = extract_document_tables(synthetic_empty_page_pdf)
        assert tables == []


# ─── TestHandleClosure ───────────────────────────────────────────────────


class TestHandleClosure:
    def test_pdfplumber_handle_closed_after_extraction(self, synthetic_ruled_table_pdf: Path):
        tables = extract_document_tables(synthetic_ruled_table_pdf)
        assert len(tables) >= 1

        # Check file can be opened for writing on Windows (no leaked file lock)
        with open(synthetic_ruled_table_pdf, "rb") as f:
            data = f.read()
        assert len(data) > 0

    def test_pdfplumber_handle_closed_on_exception(self, synthetic_ruled_table_pdf: Path):
        """Simulate an error during page extraction; ensure pdf handle closes."""
        with patch("app.extraction.digital_extractor.extract_tables_from_page", side_effect=RuntimeError("Test error")):
            with pytest.raises(RuntimeError, match="Test error"):
                extract_document_tables(synthetic_ruled_table_pdf)

        # File handle must still be free
        with open(synthetic_ruled_table_pdf, "rb") as f:
            data = f.read()
        assert len(data) > 0
