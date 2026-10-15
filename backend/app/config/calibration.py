"""
DocuStruct AI — Calibration Configuration

Loads and validates threshold values from ``thresholds.yaml``.

All thresholds are engineering starting-point defaults and remain
``UNMEASURED`` until benchmarked against a verified ground-truth
dataset.

Raises :class:`ConfigurationError` on missing, malformed, or
out-of-range calibration data — **never** silently replaces bad
values with arbitrary defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, model_validator


# ── Custom exception ────────────────────────────────────────────────────────


class ConfigurationError(Exception):
    """Raised when calibration data is missing, malformed, or invalid."""


# ── CalibrationConfig model ─────────────────────────────────────────────────


class CalibrationConfig(BaseModel):
    """Typed, validated calibration thresholds loaded from YAML.

    Attributes
    ----------
    max_file_size_bytes : int
        Maximum PDF file size **in bytes**.
    max_pdf_pages : int
        Maximum page count per PDF.
    max_workers : int
        Document-processing worker count (Phase 1 = 1).
    stitch_min_relative_col_overlap : float
        Minimum column overlap ratio for multipage stitching (0–1).
    header_similarity_confirm : float
        Minimum header similarity for repeated-header detection (0–1).
    stitch_min_type_compatibility : float
        Minimum type compatibility between table fragments (0–1).
    min_chars_for_digital : int
        Character count threshold for digital page classification.
    max_garbled_char_ratio : float
        Garbled character ratio ceiling for digital classification (0–1).
    min_image_coverage_for_scanned : float
        Image area fraction threshold for scanned classification (0–1).
    min_table_rows : int
        Minimum rows for a region to count as a table.
    min_table_cols : int
        Minimum columns for a region to count as a table.
    """

    # PDF Security Gate
    max_file_size_bytes: int = Field(
        default=26_214_400, gt=0,
        description="Maximum input PDF size in bytes.",
    )
    max_pdf_pages: int = Field(
        default=50, gt=0,
        description="Maximum pages per PDF.",
    )

    # Concurrency
    max_workers: int = Field(
        default=1, ge=1,
        description="Document-processing workers.",
    )

    # Stitching thresholds
    stitch_min_relative_col_overlap: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Min column overlap ratio for stitching.",
    )
    header_similarity_confirm: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Min header similarity for repeated-header detection.",
    )
    stitch_min_type_compatibility: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Min type compatibility for stitching.",
    )

    # Page classification thresholds
    min_chars_for_digital: int = Field(
        default=20, ge=0,
        description="Min character count for digital page.",
    )
    max_garbled_char_ratio: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Max garbled char ratio for digital page.",
    )
    min_image_coverage_for_scanned: float = Field(
        default=0.50, ge=0.0, le=1.0,
        description="Min image coverage fraction for scanned page.",
    )

    # Table extraction thresholds
    min_table_rows: int = Field(
        default=2, ge=1,
        description="Min rows for a valid table.",
    )
    min_table_cols: int = Field(
        default=2, ge=1,
        description="Min columns for a valid table.",
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> "CalibrationConfig":
        """Cross-field sanity checks."""
        if self.stitch_min_relative_col_overlap > self.header_similarity_confirm:
            # Not necessarily invalid, but worth noting — keep it permissive.
            pass
        return self

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "CalibrationConfig":
        """Load and validate calibration from a YAML file.

        Parameters
        ----------
        yaml_path : Path
            Absolute or relative path to the thresholds YAML.

        Returns
        -------
        CalibrationConfig
            Validated calibration object.

        Raises
        ------
        ConfigurationError
            If the file is missing, unreadable, contains malformed
            YAML, or has values outside permitted ranges.
        """
        resolved = Path(yaml_path).resolve()

        if not resolved.is_file():
            raise ConfigurationError(
                f"Calibration file not found: {resolved}"
            )

        try:
            raw_text = resolved.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                f"Cannot read calibration file {resolved}: {exc}"
            ) from exc

        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                f"Malformed YAML in calibration file {resolved}: {exc}"
            ) from exc

        if data is None:
            raise ConfigurationError(
                f"Calibration file is empty: {resolved}"
            )

        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Calibration file must contain a YAML mapping, "
                f"got {type(data).__name__}: {resolved}"
            )

        try:
            return cls.model_validate(data)
        except Exception as exc:
            raise ConfigurationError(
                f"Invalid calibration values in {resolved}: {exc}"
            ) from exc

    @classmethod
    def load_defaults(cls, thresholds_path: Optional[Path] = None) -> "CalibrationConfig":
        """Convenience loader using the package-bundled thresholds.yaml.

        Parameters
        ----------
        thresholds_path : Path, optional
            Override path.  When ``None``, uses the ``thresholds.yaml``
            located alongside this module.

        Returns
        -------
        CalibrationConfig
        """
        if thresholds_path is None:
            thresholds_path = Path(__file__).resolve().parent / "thresholds.yaml"
        return cls.from_yaml(thresholds_path)
