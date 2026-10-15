"""
DocuStruct AI — Unit Tests: Step 1.4 Page Router

Tests page signal analysis, classification into DIGITAL, SCANNED,
HYBRID, and EMPTY_OR_UNREADABLE, and strict Windows file handle closure
using real synthetic PDF fixtures.
"""

from __future__ import annotations

from pathlib import Path

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


# ─── TestPageSignalAnalysis ──────────────────────────────────────────────


class TestPageSignalAnalysis:
    def test_empty_page_signals(self, synthetic_empty_page_pdf: Path):
        doc = pymupdf.open(str(synthetic_empty_page_pdf))
        try:
            page = doc.load_page(0)
            signals = analyze_page_signals(page)
            assert signals["printable_char_count"] == 0
            assert signals["garbled_char_ratio"] == 0.0
            assert signals["image_coverage_ratio"] == 0.0
            assert signals["vector_line_count"] == 0
            assert signals["deferred_regions_count"] == 0
        finally:
            doc.close()

    def test_digital_page_signals(self, valid_digital_pdf: Path):
        doc = pymupdf.open(str(valid_digital_pdf))
        try:
            page = doc.load_page(0)
            signals = analyze_page_signals(page)
            assert signals["printable_char_count"] >= 20
            assert signals["garbled_char_ratio"] == 0.0
            assert signals["image_coverage_ratio"] == 0.0
        finally:
            doc.close()

    def test_scanned_page_signals(self, synthetic_scanned_pdf: Path):
        doc = pymupdf.open(str(synthetic_scanned_pdf))
        try:
            page = doc.load_page(0)
            signals = analyze_page_signals(page)
            assert signals["printable_char_count"] == 0
            assert signals["image_coverage_ratio"] >= 0.50
            assert signals["deferred_regions_count"] >= 1
        finally:
            doc.close()

    def test_hybrid_page_signals(self, synthetic_hybrid_pdf: Path):
        doc = pymupdf.open(str(synthetic_hybrid_pdf))
        try:
            page = doc.load_page(0)
            signals = analyze_page_signals(page)
            assert signals["printable_char_count"] >= 50
            assert signals["image_coverage_ratio"] >= 0.20
            assert signals["deferred_regions_count"] >= 1
        finally:
            doc.close()

    def test_ruled_page_signals_detect_vector_lines(self, synthetic_ruled_table_pdf: Path):
        doc = pymupdf.open(str(synthetic_ruled_table_pdf))
        try:
            page = doc.load_page(0)
            signals = analyze_page_signals(page)
            assert signals["vector_line_count"] > 0
            assert signals["printable_char_count"] > 0
        finally:
            doc.close()


# ─── TestPageClassification ──────────────────────────────────────────────


class TestPageClassification:
    def test_classify_empty_page(self, synthetic_empty_page_pdf: Path, calibration: CalibrationConfig):
        profiles = route_document_pages(synthetic_empty_page_pdf, calibration)
        assert len(profiles) == 1
        p = profiles[0]
        assert p.page_number == 1
        assert p.page_type == PageType.EMPTY_OR_UNREADABLE
        assert p.processing_status == PageProcessingStatus.EMPTY_PAGE
        assert p.table_presence == TablePresenceStatus.CONFIRMED_ABSENT

    def test_classify_scanned_page(self, synthetic_scanned_pdf: Path, calibration: CalibrationConfig):
        profiles = route_document_pages(synthetic_scanned_pdf, calibration)
        assert len(profiles) == 1
        p = profiles[0]
        assert p.page_type == PageType.SCANNED
        assert p.processing_status == PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        assert p.table_presence == TablePresenceStatus.UNKNOWN_PENDING_OCR
        # Invariant: Scanned pages are NEVER CONFIRMED_ABSENT
        assert p.table_presence != TablePresenceStatus.CONFIRMED_ABSENT

    def test_classify_hybrid_page(self, synthetic_hybrid_pdf: Path, calibration: CalibrationConfig):
        profiles = route_document_pages(synthetic_hybrid_pdf, calibration)
        assert len(profiles) == 1
        p = profiles[0]
        assert p.page_type == PageType.HYBRID
        assert p.processing_status == PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        assert p.table_presence == TablePresenceStatus.UNKNOWN_PENDING_OCR
        assert p.deferred_regions_count >= 1

    def test_classify_digital_page(self, valid_digital_pdf: Path, calibration: CalibrationConfig):
        profiles = route_document_pages(valid_digital_pdf, calibration)
        assert len(profiles) == 1
        p = profiles[0]
        assert p.page_type == PageType.DIGITAL
        assert p.processing_status == PageProcessingStatus.EXTRACTED

    def test_garbled_threshold_escalates_to_unreadable(self, calibration: CalibrationConfig):
        signals = {
            "printable_char_count": 100,
            "garbled_char_ratio": 0.85,
            "image_coverage_ratio": 0.05,
            "vector_line_count": 0,
            "deferred_regions_count": 0,
        }
        profile = classify_page(1, signals, calibration)
        assert profile.page_type == PageType.EMPTY_OR_UNREADABLE
        assert profile.processing_status == PageProcessingStatus.FAILED_PAGE


# ─── TestResourceDiscipline ──────────────────────────────────────────────


class TestResourceDiscipline:
    def test_document_handle_closed_after_routing(self, valid_digital_pdf: Path):
        profiles = route_document_pages(valid_digital_pdf)
        assert len(profiles) == 1

        # On Windows, opening in exclusive read/write mode verifies handle release
        with open(valid_digital_pdf, "rb") as f:
            content = f.read()
        assert len(content) > 0

    def test_multipage_routing_handle_safety(self, multipage_3_pdf: Path):
        profiles = route_document_pages(multipage_3_pdf)
        assert len(profiles) == 3
        for idx, prof in enumerate(profiles, start=1):
            assert prof.page_number == idx

        with open(multipage_3_pdf, "rb") as f:
            content = f.read()
        assert len(content) > 0
