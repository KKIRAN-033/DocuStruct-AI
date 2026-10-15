"""
DocuStruct AI — PDF Ingestion Security Gate

Validates input files before any extraction work begins.  Enforces
size limits, PDF signature checks, structure integrity, password /
zero-page rejection, UUID workspace isolation, path-traversal
prevention, and Windows-safe resource cleanup.

Design invariants (from MASTER_DIRECTIVE.md Section 10):
    - The user's original input file is **never** deleted.
    - All ``fitz.Document`` handles are closed in ``finally`` blocks.
    - Confidential file contents are never logged.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

from app.config.settings import AppSettings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Exception hierarchy
# ═══════════════════════════════════════════════════════════════════════════


class SecurityGateError(Exception):
    """Base exception for all security gate validation failures."""


class FileNotFoundValidationError(SecurityGateError):
    """Input file does not exist or is not a regular file."""


class InvalidFileTypeError(SecurityGateError):
    """Input file is empty or not a recognisable type."""


class FileSizeExceededError(SecurityGateError):
    """Input file exceeds the maximum permitted size."""


class InvalidPDFSignatureError(SecurityGateError):
    """File does not contain a valid ``%PDF-`` header signature."""


class EncryptedPDFError(SecurityGateError):
    """PDF is encrypted or password-protected."""


class CorruptPDFError(SecurityGateError):
    """PDF fails structural parsing by PyMuPDF."""


class PageCountExceededError(SecurityGateError):
    """PDF has zero pages or exceeds the maximum page limit."""


class PathTraversalError(SecurityGateError):
    """Detected an attempt to escape the workspace directory."""


# ═══════════════════════════════════════════════════════════════════════════
# PDF inspection and validation
# ═══════════════════════════════════════════════════════════════════════════


def inspect_and_validate_pdf(
    file_path: Path,
    settings: Optional[AppSettings] = None,
) -> dict[str, Any]:
    """Validate an input PDF against all security gate rules.

    Parameters
    ----------
    file_path : Path
        Path to the candidate PDF file.
    settings : AppSettings, optional
        Application settings.  Defaults are used when ``None``.

    Returns
    -------
    dict
        Metadata about the validated PDF:
        ``page_count``, ``format``, ``is_encrypted``, ``file_size_bytes``.

    Raises
    ------
    FileNotFoundValidationError
        If the file does not exist or is not a regular file.
    InvalidFileTypeError
        If the file is empty.
    FileSizeExceededError
        If the file exceeds ``settings.max_file_size_bytes``.
    InvalidPDFSignatureError
        If the first 1024 bytes do not contain ``%PDF-``.
    CorruptPDFError
        If PyMuPDF cannot parse the file.
    EncryptedPDFError
        If the PDF is encrypted or password-protected.
    PageCountExceededError
        If the PDF has zero pages or exceeds ``settings.max_pdf_pages``.
    """
    if settings is None:
        settings = AppSettings()

    resolved = Path(file_path).resolve()

    # 1. Existence and regular file
    if not resolved.exists():
        raise FileNotFoundValidationError(
            f"Input file does not exist: {resolved}"
        )
    if not resolved.is_file():
        raise FileNotFoundValidationError(
            f"Input path is not a regular file: {resolved}"
        )

    # 2. Empty file
    file_size = resolved.stat().st_size
    if file_size == 0:
        raise InvalidFileTypeError("Input file is empty (0 bytes).")

    # 3. Size limit
    if file_size > settings.max_file_size_bytes:
        raise FileSizeExceededError(
            f"File size ({file_size:,} bytes) exceeds maximum "
            f"({settings.max_file_size_bytes:,} bytes / "
            f"{settings.max_file_size_bytes / (1024 * 1024):.0f} MiB)."
        )

    # 4. PDF signature (%PDF- in first 1024 bytes)
    try:
        with open(resolved, "rb") as fh:
            header = fh.read(1024)
    except OSError as exc:
        raise InvalidFileTypeError(
            f"Cannot read file header: {exc}"
        ) from exc

    if b"%PDF-" not in header:
        raise InvalidPDFSignatureError(
            "File does not contain a valid %PDF- header signature."
        )

    # 5. Structural validation with PyMuPDF
    doc: Optional[fitz.Document] = None
    try:
        try:
            doc = fitz.open(str(resolved))
        except Exception as exc:
            raise CorruptPDFError(
                f"PyMuPDF cannot parse this file: {exc}"
            ) from exc

        # 6. Encrypted / password-protected
        if doc.is_encrypted or doc.needs_pass:
            raise EncryptedPDFError(
                "PDF is encrypted or password-protected. "
                "Encrypted PDFs are not supported."
            )

        # 7. Zero-page PDF
        page_count = doc.page_count
        if page_count == 0:
            raise PageCountExceededError(
                "PDF contains zero pages."
            )

        # 8. Page limit
        if page_count > settings.max_pdf_pages:
            raise PageCountExceededError(
                f"PDF page count ({page_count}) exceeds maximum "
                f"({settings.max_pdf_pages})."
            )

        metadata: dict[str, Any] = {
            "page_count": page_count,
            "format": doc.metadata.get("format", "PDF") if doc.metadata else "PDF",
            "is_encrypted": False,
            "file_size_bytes": file_size,
        }

    finally:
        if doc is not None:
            doc.close()

    return metadata


# ═══════════════════════════════════════════════════════════════════════════
# Filename sanitisation
# ═══════════════════════════════════════════════════════════════════════════


def sanitize_filename(filename: str) -> str:
    """Strip directory components, path separators, and null bytes.

    Returns only the final name component via ``pathlib.Path.name``.
    """
    # Remove null bytes that could confuse filesystem APIs
    cleaned = filename.replace("\x00", "")
    # Extract the basename only
    name = Path(cleaned).name
    # Final safety: strip any remaining path separators
    name = name.replace("/", "").replace("\\", "")
    if not name:
        name = "unnamed_document"
    return name


# ═══════════════════════════════════════════════════════════════════════════
# Workspace isolation
# ═══════════════════════════════════════════════════════════════════════════


def create_job_workspace(
    job_id: Optional[str] = None,
    base_dir: Optional[Path] = None,
    settings: Optional[AppSettings] = None,
) -> Path:
    """Create an isolated UUID-based job workspace directory.

    Parameters
    ----------
    job_id : str, optional
        Job identifier.  Generated as a UUID4 if not provided.
    base_dir : Path, optional
        Parent directory.  Falls back to ``settings.workspace_root``.
    settings : AppSettings, optional
        Application settings.

    Returns
    -------
    Path
        Absolute path to the new workspace directory.

    Raises
    ------
    PathTraversalError
        If the resulting directory escapes the base directory.
    """
    if settings is None:
        settings = AppSettings()

    if job_id is None:
        job_id = str(uuid.uuid4())

    if base_dir is None:
        base_dir = settings.workspace_root

    base_resolved = base_dir.resolve()
    workspace = (base_resolved / job_id).resolve()

    # Path traversal check
    if not str(workspace).startswith(str(base_resolved)):
        raise PathTraversalError(
            f"Workspace path escapes base directory: "
            f"workspace={workspace}, base={base_resolved}"
        )

    # Use parents=True to create base_dir if it doesn't exist yet
    workspace.mkdir(parents=True, exist_ok=False)
    return workspace


# ═══════════════════════════════════════════════════════════════════════════
# Workspace cleanup
# ═══════════════════════════════════════════════════════════════════════════


def cleanup_job_workspace(
    workspace_dir: Path,
    original_input_path: Optional[Path] = None,
) -> bool:
    """Remove a job workspace directory safely.

    Safety invariant: ``original_input_path`` is **never** deleted.
    If the original input file is located inside the workspace
    directory (which should not happen but is defended against),
    the workspace is **not** deleted.

    Parameters
    ----------
    workspace_dir : Path
        Workspace to remove.
    original_input_path : Path, optional
        Path to the user's original input file.

    Returns
    -------
    bool
        ``True`` if the workspace was successfully removed;
        ``False`` if cleanup failed (e.g. Windows file lock).
    """
    workspace_resolved = workspace_dir.resolve()

    if not workspace_resolved.exists():
        return True  # Nothing to clean up

    # Safety: ensure original input is not inside the workspace
    if original_input_path is not None:
        original_resolved = original_input_path.resolve()
        try:
            if original_resolved.is_relative_to(workspace_resolved):
                logger.warning(
                    "Original input file is inside the workspace directory — "
                    "skipping workspace cleanup to protect user data."
                )
                return False
        except (ValueError, TypeError):
            pass  # is_relative_to raised — paths are unrelated, safe to proceed

    try:
        shutil.rmtree(workspace_resolved)
        return True
    except PermissionError:
        logger.warning(
            "Cannot remove workspace directory (Windows file lock likely): %s",
            workspace_resolved,
        )
        return False
    except OSError as exc:
        logger.warning(
            "Workspace cleanup failed: %s — %s",
            workspace_resolved,
            exc,
        )
        return False
