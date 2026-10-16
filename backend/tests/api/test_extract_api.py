"""DocuStruct AI — Extraction API Integration Tests.

Tests ``POST /api/v1/extract`` for:
    - Valid digital PDF extraction (ruled table).
    - Digital PDF with no tables.
    - Scanned-only PDF (deferred to OCR).
    - Corrupt PDF (operational failure).
    - Encrypted PDF (operational failure).
    - Oversized upload (HTTP 413).
    - Temporary file cleanup guarantee.
    - Response serialization parity with TypeScript contracts.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)


# ── Fixture Helpers ──────────────────────────────────────────────────────────
# Integration tests use TestClient directly, so we generate PDFs inline
# rather than relying on pytest fixture injection.


def _make_ruled_table_pdf() -> bytes:
    """Create a 1-page PDF with drawn grid lines and tabular text."""
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=612, height=792)
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols, rows = 3, 3

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

        data = [
            ["Account", "Amount", "Status"],
            ["0012345", "1,234.56", "Active"],
            ["0067890", "(450.50)", "Pending"],
        ]
        for r, row in enumerate(data):
            for c, cell_text in enumerate(row):
                x = x_start + c * col_w + 10
                y = y_start + r * row_h + 20
                page.insert_text((x, y), cell_text, fontsize=9)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    finally:
        doc.close()


def _make_no_tables_pdf() -> bytes:
    """Create a digital PDF with prose paragraphs but no tables."""
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=595, height=842)
        paragraphs = [
            "This document contains only plain text paragraphs.",
            "There are no tables, grids, or column-aligned data.",
            "It should result in COMPLETED execution but FAILED verification.",
            "Because no extractable tables are present in the content.",
        ]
        y = 72
        for p in paragraphs:
            page.insert_text((72, y), p, fontsize=10)
            y += 40
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    finally:
        doc.close()


def _make_scanned_pdf() -> bytes:
    """Create a scanned-only PDF (large image coverage, no text)."""
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=500, height=500)
        pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 50, 50), False)
        page.insert_image(pymupdf.Rect(50, 50, 450, 450), pixmap=pix)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    finally:
        doc.close()


def _make_corrupt_pdf() -> bytes:
    """Create bytes with a valid %PDF- header but truncated body."""
    return b"%PDF-1.4\n%%EOF\nGARBAGE CORRUPT DATA"


def _make_encrypted_pdf() -> bytes:
    """Create an AES-256 encrypted PDF."""
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Secret content", fontsize=12)
        buf = io.BytesIO()
        doc.save(
            buf,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="testpassword",
            owner_pw="ownerpassword",
        )
        return buf.getvalue()
    finally:
        doc.close()


def _upload(pdf_bytes: bytes, filename: str = "test.pdf") -> dict:
    """Upload PDF bytes via the extract endpoint and return the response dict."""
    response = client.post(
        "/api/v1/extract",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    return {"status_code": response.status_code, "body": response.json()}


# ── Valid PDF Extraction ─────────────────────────────────────────────────────


class TestExtractValidPDF:
    """POST /api/v1/extract with valid, parseable PDFs."""

    def test_extract_valid_digital_pdf(self) -> None:
        """A ruled-table PDF should extract successfully with tables."""
        result = _upload(_make_ruled_table_pdf())
        assert result["status_code"] == 200

        body = result["body"]
        assert body["execution_state"] == "COMPLETED"
        assert body["verification_status"] in ("VERIFIED", "VERIFIED_WITH_WARNINGS")
        assert len(body["canonical_tables"]) >= 1

    def test_extract_zero_tables_digital_pdf(self) -> None:
        """A digital PDF with no tables should complete but report no tables."""
        result = _upload(_make_no_tables_pdf())
        assert result["status_code"] == 200

        body = result["body"]
        assert body["execution_state"] == "COMPLETED"
        assert body["verification_status"] == "FAILED"
        assert "NO_TABLES_FOUND" in body["status_reason_codes"]

    def test_extract_scanned_only_pdf(self) -> None:
        """A scanned-only PDF should defer extraction to OCR."""
        result = _upload(_make_scanned_pdf())
        assert result["status_code"] == 200

        body = result["body"]
        assert body["execution_state"] == "COMPLETED"
        assert body["verification_status"] == "REVIEW_REQUIRED"
        assert "OCR_REQUIRED_FOR_SCANNED_CONTENT" in body["status_reason_codes"]


# ── Operational Failure Paths ────────────────────────────────────────────────


class TestExtractOperationalFailures:
    """Operational errors return HTTP 200 with execution_state=FAILED."""

    def test_extract_corrupt_pdf(self) -> None:
        """A corrupt PDF returns FAILED with a CORRUPT_PDF reason code."""
        result = _upload(_make_corrupt_pdf())
        assert result["status_code"] == 200

        body = result["body"]
        assert body["execution_state"] == "FAILED"
        assert "CORRUPT_PDF" in body["status_reason_codes"]

    def test_extract_encrypted_pdf(self) -> None:
        """An encrypted PDF returns FAILED with an ENCRYPTED_PDF reason code."""
        result = _upload(_make_encrypted_pdf())
        assert result["status_code"] == 200

        body = result["body"]
        assert body["execution_state"] == "FAILED"
        assert "ENCRYPTED_PDF" in body["status_reason_codes"]


# ── Upload Boundary ─────────────────────────────────────────────────────────


class TestUploadLimits:
    """Enforce the 50 MiB upload ceiling."""

    def test_extract_oversized_file_rejected_413(self) -> None:
        """Uploading > 50 MiB should return HTTP 413 Payload Too Large."""
        # Create a payload just over 50 MiB (52,428,800 + 1024 bytes)
        oversized = b"%PDF-1.4\n" + (b"\x00" * (52_428_800 + 1024 - 9))
        response = client.post(
            "/api/v1/extract",
            files={"file": ("huge.pdf", io.BytesIO(oversized), "application/pdf")},
        )
        assert response.status_code == 413
        assert "50 MiB" in response.json()["detail"]


# ── Temporary File Cleanup ───────────────────────────────────────────────────


class TestTempFileCleanup:
    """Verify that no orphaned temporary upload files remain after extraction."""

    def test_temporary_file_unlinked_on_success(self) -> None:
        """After a successful extraction, zero orphans should remain."""
        upload_dir = Path(tempfile.gettempdir()) / "docustruct_uploads"

        # Snapshot before
        before = set(upload_dir.glob("*")) if upload_dir.exists() else set()

        _upload(_make_ruled_table_pdf())

        # Snapshot after
        after = set(upload_dir.glob("*")) if upload_dir.exists() else set()
        orphans = after - before
        assert len(orphans) == 0, f"Orphaned temp files: {orphans}"

    def test_temporary_file_unlinked_on_error(self) -> None:
        """After a corrupt PDF failure, zero orphans should remain."""
        upload_dir = Path(tempfile.gettempdir()) / "docustruct_uploads"

        before = set(upload_dir.glob("*")) if upload_dir.exists() else set()

        _upload(_make_corrupt_pdf())

        after = set(upload_dir.glob("*")) if upload_dir.exists() else set()
        orphans = after - before
        assert len(orphans) == 0, f"Orphaned temp files: {orphans}"


# ── Serialization Parity ────────────────────────────────────────────────────


class TestSerializationParity:
    """Verify response serialization matches TypeScript contract expectations."""

    def test_response_serialization_parity_with_typescript(self) -> None:
        """Check that Decimal values serialize as strings and BoundingBox norms are numbers."""
        result = _upload(_make_ruled_table_pdf())
        body = result["body"]

        # Must have at least one table
        assert len(body["canonical_tables"]) >= 1
        table = body["canonical_tables"][0]

        # Walk rows and check cell serialization
        for row in table["rows"]:
            for cell in row:
                # numeric_decimal, if present, should serialize as a string (Pydantic v2 default)
                if cell.get("numeric_decimal") is not None:
                    assert isinstance(cell["numeric_decimal"], str), (
                        f"numeric_decimal should be a JSON string, got {type(cell['numeric_decimal'])}"
                    )

                # BoundingBox norm coordinates should be numbers
                bbox = cell.get("bbox")
                if bbox is not None:
                    for coord_key in ("norm_x0", "norm_y0", "norm_x1", "norm_y1"):
                        assert isinstance(bbox[coord_key], (int, float)), (
                            f"bbox.{coord_key} should be a number, got {type(bbox[coord_key])}"
                        )

    def test_top_level_report_fields_present(self) -> None:
        """Verify all expected top-level report fields exist in the response."""
        result = _upload(_make_ruled_table_pdf())
        body = result["body"]

        expected_fields = {
            "job_id",
            "source_filename",
            "execution_state",
            "verification_status",
            "status_reason_codes",
            "limitation_disclaimers",
            "page_profiles",
            "page_results",
            "canonical_tables",
            "stitch_events",
            "validation_issues",
            "correction_records",
            "peak_python_heap_bytes",
        }
        assert expected_fields.issubset(set(body.keys())), (
            f"Missing fields: {expected_fields - set(body.keys())}"
        )


# ── Event Loop Offloading ───────────────────────────────────────────────────


class TestEventLoopOffloading:
    """Verify that synchronous extraction does not block the asyncio event loop."""

    def test_extract_offloaded_to_threadpool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that synchronous pipeline execution is offloaded to a threadpool.

        Ensures the asyncio event loop remains responsive while the heavy
        synchronous extraction pipeline runs in a separate worker thread.
        """
        import threading
        import starlette.concurrency
        from app.pipeline import run_phase1_pipeline

        calling_thread = threading.current_thread()
        worker_threads = []
        target_funcs = []
        original_run_in_threadpool = starlette.concurrency.run_in_threadpool

        async def spy_run_in_threadpool(func, *args, **kwargs):
            target_funcs.append(func)
            return await original_run_in_threadpool(func, *args, **kwargs)

        def spy_pipeline(*args, **kwargs):
            worker_threads.append(threading.current_thread())
            return run_phase1_pipeline(*args, **kwargs)

        import sys
        api_module = sys.modules["app.api.app"]
        monkeypatch.setattr(api_module, "run_in_threadpool", spy_run_in_threadpool)
        monkeypatch.setattr(api_module, "run_phase1_pipeline", spy_pipeline)

        result = _upload(_make_ruled_table_pdf())
        assert result["status_code"] == 200
        assert len(target_funcs) == 1
        assert target_funcs[0] is spy_pipeline
        assert len(worker_threads) == 1
        assert worker_threads[0] != calling_thread

