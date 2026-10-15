"""
DocuStruct AI — Application Settings

Typed application configuration using pydantic-settings.  All filesystem
paths are resolved relative to the package location so that the
configuration is independent of the process working directory.

Environment variable overrides follow the ``DOCUSTRUCT_`` prefix
convention (e.g. ``DOCUSTRUCT_MAX_FILE_SIZE_BYTES=10485760``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve paths relative to this file, not the CWD.
_PACKAGE_DIR: Path = Path(__file__).resolve().parent


class AppSettings(BaseSettings):
    """Centralised, typed application settings for DocuStruct AI.

    Defaults are engineering starting-point values.  All extraction
    thresholds remain ``UNMEASURED`` until benchmarked against a
    verified ground-truth dataset.

    Attributes
    ----------
    max_file_size_bytes : int
        Maximum permitted input PDF size **in bytes** (25 MiB default).
    max_pdf_pages : int
        Maximum number of pages permitted in a single PDF.
    max_workers : int
        Number of concurrent document-processing workers.
        Phase 1 enforces ``1`` (sequential processing).
    workspace_root : Path
        Root directory for UUID-isolated temporary workspaces.
        Defaults to a ``docustruct_workspaces`` subdirectory inside the
        system temporary directory.
    enable_memory_measurement : bool
        When ``True``, enables optional ``tracemalloc`` heap measurement
        and records ``peak_python_heap_bytes``.  Note: Python heap usage
        measured by ``tracemalloc`` is **not** total operating-system
        process RAM; it excludes native-library allocations.
    thresholds_path : Optional[Path]
        Path to ``thresholds.yaml``.  Defaults to the file shipped
        alongside this module; resolved relative to the package so the
        setting is CWD-independent.
    """

    model_config = SettingsConfigDict(
        env_prefix="DOCUSTRUCT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- PDF Security Gate ---------------------------------------------------
    max_file_size_bytes: int = Field(
        default=26_214_400,
        gt=0,
        description="Maximum input PDF size in bytes (25 MiB).",
    )
    max_pdf_pages: int = Field(
        default=50,
        gt=0,
        description="Maximum number of pages per PDF.",
    )

    # --- Concurrency ---------------------------------------------------------
    max_workers: int = Field(
        default=1,
        ge=1,
        description="Document-processing workers (Phase 1 = 1).",
    )

    # --- Filesystem ----------------------------------------------------------
    workspace_root: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "docustruct_workspaces",
        description="Root directory for UUID-isolated temp workspaces.",
    )

    # --- Diagnostics ---------------------------------------------------------
    enable_memory_measurement: bool = Field(
        default=False,
        description=(
            "Enable tracemalloc heap measurement "
            "(peak_python_heap_bytes, not total process RAM)."
        ),
    )

    # --- Configuration paths -------------------------------------------------
    thresholds_path: Optional[Path] = Field(
        default=None,
        description="Path to thresholds.yaml.  Defaults to package-local copy.",
    )

    # -- Validators -----------------------------------------------------------

    @field_validator("thresholds_path", mode="before")
    @classmethod
    def _resolve_thresholds_path(cls, value: Optional[Path]) -> Path:
        """Fall back to the package-local thresholds.yaml when no
        explicit path is supplied, ensuring CWD-independence."""
        if value is None:
            return _PACKAGE_DIR / "thresholds.yaml"
        return Path(value).resolve()

    @field_validator("workspace_root", mode="before")
    @classmethod
    def _resolve_workspace_root(cls, value: Path) -> Path:
        return Path(value).resolve()
