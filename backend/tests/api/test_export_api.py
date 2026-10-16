"""DocuStruct AI — Table Export API Integration Tests.

Validates:
    - ``POST /api/v1/export/csv`` and ``POST /api/v1/export/json``.
    - Request shape accepts ``CanonicalTable`` directly per DECISION-009.
    - Correct HTTP status (200) and media types.
    - RFC 4180 CSV escaping for commas, quotes, and newlines.
    - Lossless JSON export preserving duplicate headers, empty headers, and column order.
    - Safe Content-Disposition filename sanitization preventing CRLF injection and quote breakout.
"""

from __future__ import annotations

import csv
import io
from fastapi.testclient import TestClient

from app.api.app import app
from app.models.domain import (
    CanonicalTable,
    CellQualityStatus,
    CellRecord,
    DataType,
)

client = TestClient(app)


# ── Fixtures & Helpers ───────────────────────────────────────────────────────


def _make_canonical_table(
    table_id: str = "table_1",
    headers: list[str] | None = None,
    rows: list[list[str]] | None = None,
) -> CanonicalTable:
    """Construct a real CanonicalTable model for testing export endpoints."""
    if headers is None:
        headers = ["Account", "Balance", "Status"]
    if rows is None:
        rows = [
            ["0012345", "1,234.56", "Active"],
            ["0067890", "(450.50)", "Pending"],
        ]

    cell_rows: list[list[CellRecord]] = []
    for r_idx, row_values in enumerate(rows):
        row_cells = []
        for c_idx, val in enumerate(row_values):
            row_cells.append(
                CellRecord(
                    table_id=table_id,
                    row_idx=r_idx,
                    col_idx=c_idx,
                    source_page=1,
                    extraction_method="LINE_BASED_RULING",
                    raw_value=val,
                    accepted_value=val,
                    data_type=DataType.STRING,
                    quality_status=CellQualityStatus.EXTRACTED_AS_IS,
                )
            )
        cell_rows.append(row_cells)

    return CanonicalTable(
        table_id=table_id,
        source_pages=[1],
        original_headers=headers,
        normalized_headers=[h.strip() for h in headers],
        header_row_count=1,
        rows=cell_rows,
        extraction_method="LINE_BASED_RULING",
        structural_checks_passed=True,
    )


# ── CSV Export Tests ────────────────────────────────────────────────────────


class TestExportCSV:
    """POST /api/v1/export/csv contract and escaping tests."""

    def test_export_csv_status_and_content_type(self) -> None:
        """Export CSV returns HTTP 200, text/csv, and attachment header."""
        table = _make_canonical_table(table_id="financial_summary")
        response = client.post(
            "/api/v1/export/csv",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert response.headers["content-disposition"] == 'attachment; filename="financial_summary.csv"'

        reader = list(csv.reader(io.StringIO(response.text)))
        assert reader[0] == ["Account", "Balance", "Status"]
        assert reader[1] == ["0012345", "1,234.56", "Active"]
        assert reader[2] == ["0067890", "(450.50)", "Pending"]

    def test_export_csv_escaping_commas_quotes_and_newlines(self) -> None:
        """CSV cells with commas, quotes, and newlines are safely quoted per RFC 4180."""
        table = _make_canonical_table(
            table_id="edge_cases",
            headers=["Name", "Quote", "Multiline"],
            rows=[
                ["Smith, John", 'Said "Hello, World"', "Line 1\nLine 2"],
                ['Doe, "Jane"', 'A "nested" phrase', "First\r\nSecond"],
            ],
        )
        response = client.post(
            "/api/v1/export/csv",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200

        # RFC 4180 parser must recover identical cell values without corruption
        reader = list(csv.reader(io.StringIO(response.text)))
        assert reader[0] == ["Name", "Quote", "Multiline"]
        assert reader[1] == ["Smith, John", 'Said "Hello, World"', "Line 1\nLine 2"]
        assert reader[2] == ['Doe, "Jane"', 'A "nested" phrase', "First\r\nSecond"]

    def test_export_csv_sanitizes_table_id_filename(self) -> None:
        """Quotes, control characters, and path separators in table_id are sanitized."""
        table = _make_canonical_table(table_id='bad"name\r\nX-Injected: true/evil')
        response = client.post(
            "/api/v1/export/csv",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200
        disposition = response.headers["content-disposition"]
        assert "\r" not in disposition
        assert "\n" not in disposition
        assert 'bad"name' not in disposition
        assert "X-Injected" not in response.headers
        assert disposition == 'attachment; filename="badnameX-Injected: trueevil.csv"'

    def test_export_csv_fallback_filename_on_empty_table_id(self) -> None:
        """Empty or only-special-char table_id falls back safely to 'table.csv'."""
        table = _make_canonical_table(table_id='""///')
        response = client.post(
            "/api/v1/export/csv",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert response.headers["content-disposition"] == 'attachment; filename="table.csv"'


# ── JSON Export Tests ───────────────────────────────────────────────────────


class TestExportJSON:
    """POST /api/v1/export/json contract and lossless preservation tests."""

    def test_export_json_status_and_content_type(self) -> None:
        """Export JSON returns HTTP 200, application/json, and attachment header."""
        table = _make_canonical_table(table_id="metrics_table")
        response = client.post(
            "/api/v1/export/json",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.headers["content-disposition"] == 'attachment; filename="metrics_table.json"'

        data = response.json()
        assert data["table_id"] == "metrics_table"
        assert data["headers"] == ["Account", "Balance", "Status"]
        assert data["rows"] == [
            ["0012345", "1,234.56", "Active"],
            ["0067890", "(450.50)", "Pending"],
        ]

    def test_export_json_preserves_duplicate_headers_losslessly(self) -> None:
        """Duplicate column headers must not overwrite values or drop columns."""
        table = _make_canonical_table(
            table_id="duplicate_headers",
            headers=["Total", "Total", "Status"],
            rows=[
                ["$100.00", "$250.00", "Verified"],
                ["$50.00", "$75.00", "Pending"],
            ],
        )
        response = client.post(
            "/api/v1/export/json",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200

        data = response.json()
        assert data["headers"] == ["Total", "Total", "Status"]
        # Both columns must be retained with their respective distinct values
        assert len(data["rows"][0]) == 3
        assert data["rows"][0] == ["$100.00", "$250.00", "Verified"]
        assert len(data["rows"][1]) == 3
        assert data["rows"][1] == ["$50.00", "$75.00", "Pending"]

    def test_export_json_preserves_empty_headers_losslessly(self) -> None:
        """Empty string headers must be preserved without collision or dropped cells."""
        table = _make_canonical_table(
            table_id="empty_headers",
            headers=["ID", "", "Notes"],
            rows=[
                ["101", "Unnamed Col Value", "Follow-up required"],
                ["102", "Another Value", "Done"],
            ],
        )
        response = client.post(
            "/api/v1/export/json",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200

        data = response.json()
        assert data["headers"] == ["ID", "", "Notes"]
        assert len(data["rows"][0]) == 3
        assert data["rows"][0][1] == "Unnamed Col Value"
        assert len(data["rows"][1]) == 3
        assert data["rows"][1][1] == "Another Value"

    def test_export_json_multiple_columns_distinct_values(self) -> None:
        """Multi-column tables preserve exact column ordering and all cell values."""
        headers = ["Col_1", "Col_2", "Col_3", "Col_4", "Col_5"]
        rows = [
            ["A1", "B1", "C1", "D1", "E1"],
            ["A2", "B2", "C2", "D2", "E2"],
            ["A3", "B3", "C3", "D3", "E3"],
        ]
        table = _make_canonical_table(table_id="wide_table", headers=headers, rows=rows)
        response = client.post(
            "/api/v1/export/json",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200

        data = response.json()
        assert data["headers"] == headers
        assert data["rows"] == rows

    def test_export_json_sanitizes_table_id_filename(self) -> None:
        """Quotes, control characters, and path separators in table_id are sanitized."""
        table = _make_canonical_table(table_id='bad"name\r\nX-Injected: true/evil')
        response = client.post(
            "/api/v1/export/json",
            json=table.model_dump(mode="json"),
        )
        assert response.status_code == 200
        disposition = response.headers["content-disposition"]
        assert "\r" not in disposition
        assert "\n" not in disposition
        assert 'bad"name' not in disposition
        assert disposition == 'attachment; filename="badnameX-Injected: trueevil.json"'

    def test_export_zip_bundles_multiple_tables(self) -> None:
        """Multiple tables are zipped into distinct RFC 4180 CSV files with UTF-8 BOM."""
        import zipfile
        t1 = _make_canonical_table(table_id="sales_orders", headers=["Order", "Total"], rows=[["ORD1", "$100"]])
        t2 = _make_canonical_table(table_id="income_stmt", headers=["Metric", "Val"], rows=[["Revenue", "$5000"]])
        response = client.post(
            "/api/v1/export/zip",
            json=[t1.model_dump(mode="json"), t2.model_dump(mode="json")],
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        namelist = zf.namelist()
        assert len(namelist) == 2
        content1 = zf.read(namelist[0]).decode("utf-8-sig")
        assert "Order" in content1
        assert "ORD1" in content1
        content2 = zf.read(namelist[1]).decode("utf-8-sig")
        assert "Revenue" in content2
