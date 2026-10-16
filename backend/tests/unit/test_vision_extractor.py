"""DocuStruct AI — Unit Tests for Vision Table Extractor

Verifies multimodal image processing, JSON parsing, CellRecord normalization,
and defensive fallback when keys are absent or network errors occur.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pymupdf
import pytest

from app.extraction.vision_extractor import (
    _clean_json_response,
    extract_tables_from_image_bytes,
    extract_tables_with_vision,
)
from app.models.domain import CanonicalTable
from app.models.state import DataType


class TestVisionExtractor:
    """Test suite for Vision AI table extraction functions."""

    def test_clean_json_response_with_markdown_fences(self) -> None:
        """Markdown code blocks are stripped properly."""
        raw = "```json\n{\"tables\": [{\"title\": \"T1\"}]}\n```"
        cleaned = _clean_json_response(raw)
        assert json.loads(cleaned) == {"tables": [{"title": "T1"}]}

    def test_clean_json_response_plain(self) -> None:
        """Plain JSON without fences parses cleanly."""
        raw = "{\"tables\": []}"
        cleaned = _clean_json_response(raw)
        assert json.loads(cleaned) == {"tables": []}

    def test_extract_tables_from_image_bytes_no_credentials(self, monkeypatch) -> None:
        """Returns empty list when no provider keys are in environment."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        tables = extract_tables_from_image_bytes(b"dummy_bytes", page_number=1)
        assert tables == []

    def test_extract_tables_from_image_bytes_successful_parsing(self, monkeypatch) -> None:
        """Vision AI structured response is converted into CanonicalTable and CellRecords."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-mock")

        mock_payload = {
            "tables": [
                {
                    "title": "Vendor Statement",
                    "headers": ["Item", "Quantity", "Amount"],
                    "rows": [
                        ["Consulting Services", "10", "$1,500.00"],
                        ["Software License", "1", "$250.50"],
                    ],
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": json.dumps(mock_payload)}}
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            tables = extract_tables_from_image_bytes(
                image_bytes=b"dummy_png_bytes",
                page_number=1,
                page_width=600.0,
                page_height=800.0,
            )

        assert len(tables) == 1
        tbl = tables[0]
        assert isinstance(tbl, CanonicalTable)
        assert tbl.table_id == "p1_v1"
        assert tbl.title == "Vendor Statement"
        assert tbl.original_headers == ["Item", "Quantity", "Amount"]
        assert len(tbl.rows) == 2

        # Check CellRecord normalization
        row1_amount = tbl.rows[0][2]
        assert row1_amount.raw_value == "$1,500.00"
        assert row1_amount.numeric_decimal == Decimal("1500.00")
        assert row1_amount.data_type == DataType.DECIMAL
        assert row1_amount.extraction_method == "VISION_AI"
        assert tbl.structural_checks_passed is True

    def test_extract_tables_with_vision_on_pymupdf_page(self, monkeypatch) -> None:
        """Renders page pixmap and coordinates with vision extraction."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-mock")

        doc = pymupdf.open()
        page = doc.new_page(width=500, height=500)
        page.insert_text(pymupdf.Point(50, 50), "Test Sample")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "{\"tables\": []}"}}]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            tables = extract_tables_with_vision(page, page_number=1)

        doc.close()
        assert tables == []
