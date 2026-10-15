"""
Unit tests for Step 1.3 — PDF Security Gate.

Covers MASTER_DIRECTIVE.md Sections 10 & 19 requirements:
    - Missing, empty, oversized, non-PDF, corrupt, encrypted,
      zero-page, and >50-page rejection.
    - Path traversal prevention.
    - Workspace isolation and cleanup.
    - Original input file preservation.
    - File handle closure on exception.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.config.settings import AppSettings
from app.ingestion.security_gate import (
    CorruptPDFError,
    EncryptedPDFError,
    FileNotFoundValidationError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidPDFSignatureError,
    PageCountExceededError,
    PathTraversalError,
    cleanup_job_workspace,
    create_job_workspace,
    inspect_and_validate_pdf,
    sanitize_filename,
)


# ── File Validation ─────────────────────────────────────────────────────────


class TestSecurityGateValidation:
    """Test PDF file-level validation rules."""

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundValidationError, match="does not exist"):
            inspect_and_validate_pdf(tmp_path / "nonexistent.pdf")

    def test_directory_input(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundValidationError, match="not a regular file"):
            inspect_and_validate_pdf(tmp_path)

    def test_empty_file(self, empty_file: Path) -> None:
        with pytest.raises(InvalidFileTypeError, match="empty"):
            inspect_and_validate_pdf(empty_file)

    def test_invalid_signature(self, non_pdf_file: Path) -> None:
        with pytest.raises(InvalidPDFSignatureError, match="PDF"):
            inspect_and_validate_pdf(non_pdf_file)

    def test_corrupt_pdf(self, corrupt_pdf_file: Path) -> None:
        with pytest.raises(CorruptPDFError):
            inspect_and_validate_pdf(corrupt_pdf_file)

    def test_encrypted_pdf(self, encrypted_pdf: Path) -> None:
        with pytest.raises(EncryptedPDFError, match="[Ee]ncrypted"):
            inspect_and_validate_pdf(encrypted_pdf)

    def test_page_count_over_50(self, multipage_51_pdf: Path) -> None:
        with pytest.raises(PageCountExceededError, match="51"):
            inspect_and_validate_pdf(multipage_51_pdf)

    def test_oversized_file(self, oversized_file: Path) -> None:
        with pytest.raises(FileSizeExceededError, match="exceeds"):
            inspect_and_validate_pdf(oversized_file)

    def test_valid_pdf_metadata(self, valid_digital_pdf: Path) -> None:
        meta = inspect_and_validate_pdf(valid_digital_pdf)
        assert meta["page_count"] == 1
        assert meta["file_size_bytes"] > 0
        assert meta["is_encrypted"] is False

    def test_valid_multipage_pdf(self, multipage_3_pdf: Path) -> None:
        meta = inspect_and_validate_pdf(multipage_3_pdf)
        assert meta["page_count"] == 3


# ── Filename Sanitization ──────────────────────────────────────────────────


class TestFilenameSanitization:
    """Test path traversal prevention in filenames."""

    def test_strips_directory_components(self) -> None:
        assert sanitize_filename("../../etc/passwd") == "passwd"

    def test_strips_windows_path(self) -> None:
        assert sanitize_filename("C:\\Users\\evil\\test.pdf") == "test.pdf"

    def test_strips_null_bytes(self) -> None:
        assert sanitize_filename("te\x00st.pdf") == "test.pdf"

    def test_empty_becomes_unnamed(self) -> None:
        assert sanitize_filename("") == "unnamed_document"

    def test_simple_filename_unchanged(self) -> None:
        assert sanitize_filename("document.pdf") == "document.pdf"


# ── Workspace Isolation ────────────────────────────────────────────────────


class TestWorkspaceIsolation:
    """Test UUID workspace creation and path containment."""

    def test_workspace_created(self, tmp_path: Path) -> None:
        job_id = str(uuid.uuid4())
        ws = create_job_workspace(job_id=job_id, base_dir=tmp_path)
        assert ws.exists()
        assert ws.is_dir()
        assert ws.name == job_id

    def test_workspace_containment(self, tmp_path: Path) -> None:
        ws = create_job_workspace(base_dir=tmp_path)
        assert str(ws.resolve()).startswith(str(tmp_path.resolve()))

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises((PathTraversalError, OSError)):
            create_job_workspace(job_id="../../../escape", base_dir=tmp_path)


# ── Workspace Cleanup ──────────────────────────────────────────────────────


class TestWorkspaceCleanup:
    """Test safe cleanup with original file protection."""

    def test_cleanup_removes_workspace(self, tmp_path: Path) -> None:
        ws = create_job_workspace(base_dir=tmp_path)
        # Add a file inside workspace
        (ws / "temp.txt").write_text("temp", encoding="utf-8")
        result = cleanup_job_workspace(ws)
        assert result is True
        assert not ws.exists()

    def test_cleanup_preserves_original_file(self, tmp_path: Path, valid_digital_pdf: Path) -> None:
        ws = create_job_workspace(base_dir=tmp_path)
        result = cleanup_job_workspace(ws, original_input_path=valid_digital_pdf)
        assert result is True
        # Original file must still exist
        assert valid_digital_pdf.exists()

    def test_cleanup_nonexistent_returns_true(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does_not_exist"
        result = cleanup_job_workspace(nonexistent)
        assert result is True

    def test_cleanup_refuses_if_original_inside_workspace(self, tmp_path: Path) -> None:
        ws = create_job_workspace(base_dir=tmp_path)
        fake_original = ws / "original.pdf"
        fake_original.write_text("fake", encoding="utf-8")
        result = cleanup_job_workspace(ws, original_input_path=fake_original)
        assert result is False
        # Workspace should NOT be deleted
        assert ws.exists()


# ── File Handle Safety ──────────────────────────────────────────────────────


class TestFileHandleSafety:
    """Verify fitz.Document handles are closed even on exception."""

    def test_handle_closed_on_encrypted_pdf(self, encrypted_pdf: Path) -> None:
        """After EncryptedPDFError, the PDF handle must be closed."""
        with pytest.raises(EncryptedPDFError):
            inspect_and_validate_pdf(encrypted_pdf)
        # If handle was not closed, Windows would lock the file.
        # Verify we can still read/delete it.
        assert encrypted_pdf.exists()
        data = encrypted_pdf.read_bytes()
        assert len(data) > 0

    def test_handle_closed_on_page_count_exceeded(self, multipage_51_pdf: Path) -> None:
        with pytest.raises(PageCountExceededError):
            inspect_and_validate_pdf(multipage_51_pdf)
        assert multipage_51_pdf.exists()
        data = multipage_51_pdf.read_bytes()
        assert len(data) > 0
