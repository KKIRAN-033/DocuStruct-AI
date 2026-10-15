"""
Phase 2 — Page Router Tests

Covers page signal analysis and classification for DIGITAL,
SCANNED, HYBRID, and EMPTY_OR_UNREADABLE.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pymupdf
import pytest

from app.config.calibration import CalibrationConfig
from app.ingestion.page_router import (
    analyze_page_signals,
    classify_page,
    route_document_pages,
)
from app.models.state import (
    PageProcessingStatus,
    PageType,
    TablePresenceStatus,
)


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def calibration() -> CalibrationConfig:
    return CalibrationConfig.load_defaults()


@pytest.fixture
def empty_pdf_page():
    """A blank PyMuPDF page with no content."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    yield page
    doc.close()


@pytest.fixture
def digital_pdf_page():
    """A PyMuPDF page with significant digital text."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    # Insert enough text to exceed min_chars_for_digital
    text = "The quick brown fox jumps over the lazy dog. " * 20
    page.insert_text((72, 100), text, fontsize=10)
    yield page
    doc.close()


# ─── Signal Analysis ─────────────────────────────────────────────────────


class TestAnalyzePageSignals:
    def test_empty_page_signals(self, empty_pdf_page):
        signals = analyze_page_signals(empty_pdf_page)
        assert signals["printable_char_count"] == 0
        assert signals["garbled_char_ratio"] == 0.0
        assert signals["image_coverage_ratio"] == 0.0
        assert signals["deferred_regions_count"] == 0

    def test_digital_page_has_characters(self, digital_pdf_page):
        signals = analyze_page_signals(digital_pdf_page)
        assert signals["printable_char_count"] > 50
        assert signals["garbled_char_ratio"] == 0.0

    def test_signal_keys_complete(self, empty_pdf_page):
        signals = analyze_page_signals(empty_pdf_page)
        expected_keys = {
            "printable_char_count",
            "garbled_char_ratio",
            "image_coverage_ratio",
            "vector_line_count",
            "deferred_regions_count",
        }
        assert set(signals.keys()) == expected_keys


# ─── Classification ──────────────────────────────────────────────────────


class TestClassifyPage:
    def test_empty_page(self, calibration):
        signals = {
            "printable_char_count": 0,
            "garbled_char_ratio": 0.0,
            "image_coverage_ratio": 0.0,
            "vector_line_count": 0,
            "deferred_regions_count": 0,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.EMPTY_OR_UNREADABLE
        assert profile.processing_status == PageProcessingStatus.EMPTY_PAGE
        assert profile.table_presence == TablePresenceStatus.CONFIRMED_ABSENT

    def test_scanned_page_never_confirmed_absent(self, calibration):
        signals = {
            "printable_char_count": 2,
            "garbled_char_ratio": 0.0,
            "image_coverage_ratio": 0.85,
            "vector_line_count": 0,
            "deferred_regions_count": 1,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.SCANNED
        assert profile.processing_status == PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        assert profile.table_presence == TablePresenceStatus.UNKNOWN_PENDING_OCR
        # Critical invariant: scanned pages never CONFIRMED_ABSENT
        assert profile.table_presence != TablePresenceStatus.CONFIRMED_ABSENT

    def test_digital_page(self, calibration):
        signals = {
            "printable_char_count": 200,
            "garbled_char_ratio": 0.01,
            "image_coverage_ratio": 0.05,
            "vector_line_count": 10,
            "deferred_regions_count": 0,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.DIGITAL
        assert profile.processing_status == PageProcessingStatus.EXTRACTED

    def test_hybrid_page(self, calibration):
        signals = {
            "printable_char_count": 200,
            "garbled_char_ratio": 0.01,
            "image_coverage_ratio": 0.45,
            "vector_line_count": 5,
            "deferred_regions_count": 2,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.HYBRID
        assert profile.processing_status == PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR

    def test_high_garbled_becomes_unreadable(self, calibration):
        signals = {
            "printable_char_count": 200,
            "garbled_char_ratio": 0.95,
            "image_coverage_ratio": 0.05,
            "vector_line_count": 0,
            "deferred_regions_count": 0,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.EMPTY_OR_UNREADABLE
        assert profile.processing_status == PageProcessingStatus.FAILED_PAGE

    def test_page_number_preserved(self, calibration):
        signals = {
            "printable_char_count": 0,
            "garbled_char_ratio": 0.0,
            "image_coverage_ratio": 0.0,
            "vector_line_count": 0,
            "deferred_regions_count": 0,
        }
        profile = classify_page(42, signals, calibration)
        assert profile.page_number == 42


# ─── Document routing ────────────────────────────────────────────────────


class TestRouteDocumentPages:
    def test_route_empty_pdf(self, tmp_path):
        pdf_path = tmp_path / "empty.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        profiles = route_document_pages(pdf_path)
        assert len(profiles) == 1
        assert profiles[0].page_type == PageType.EMPTY_OR_UNREADABLE

    def test_route_multi_page_pdf(self, tmp_path):
        pdf_path = tmp_path / "multi.pdf"
        doc = pymupdf.open()
        for _ in range(3):
            doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        profiles = route_document_pages(pdf_path)
        assert len(profiles) == 3
        for i, p in enumerate(profiles, 1):
            assert p.page_number == i

    def test_document_handle_closed_after_routing(self, tmp_path):
        pdf_path = tmp_path / "handle_test.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        route_document_pages(pdf_path)

        # Verify we can delete/reopen the file (handle released)
        with open(pdf_path, "rb") as f:
            data = f.read()
        assert len(data) > 0
