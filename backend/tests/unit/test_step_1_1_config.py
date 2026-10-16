"""
Unit tests for Step 1.1 — Configuration and Calibration.

Covers MASTER_DIRECTIVE.md Section 7 requirements:
    - Default settings loading.
    - Environment variable overrides.
    - Missing / malformed / invalid YAML.
    - Path-independent configuration loading.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config.calibration import CalibrationConfig, ConfigurationError
from app.config.settings import AppSettings


# ── Default Settings ────────────────────────────────────────────────────────


class TestDefaultSettings:
    """Verify default AppSettings match specification."""

    def test_default_max_file_size(self) -> None:
        s = AppSettings()
        assert s.max_file_size_bytes == 52_428_800  # 50 MiB

    def test_default_max_pdf_pages(self) -> None:
        s = AppSettings()
        assert s.max_pdf_pages == 100

    def test_default_max_workers(self) -> None:
        s = AppSettings()
        assert s.max_workers == 1

    def test_default_memory_measurement_disabled(self) -> None:
        s = AppSettings()
        assert s.enable_memory_measurement is False

    def test_thresholds_path_resolves_to_package(self) -> None:
        s = AppSettings()
        assert s.thresholds_path is not None
        assert s.thresholds_path.name == "thresholds.yaml"
        assert s.thresholds_path.is_file()


# ── Environment Overrides ───────────────────────────────────────────────────


class TestEnvironmentOverrides:
    """Verify DOCUSTRUCT_* environment variable overrides."""

    def test_max_file_size_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCUSTRUCT_MAX_FILE_SIZE_BYTES", "10485760")
        s = AppSettings()
        assert s.max_file_size_bytes == 10_485_760  # 10 MiB

    def test_max_pages_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCUSTRUCT_MAX_PDF_PAGES", "200")
        s = AppSettings()
        assert s.max_pdf_pages == 200

    def test_memory_measurement_enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCUSTRUCT_ENABLE_MEMORY_MEASUREMENT", "true")
        s = AppSettings()
        assert s.enable_memory_measurement is True


# ── Calibration YAML ────────────────────────────────────────────────────────


class TestCalibrationLoading:
    """Verify CalibrationConfig loading from YAML."""

    def test_load_defaults(self) -> None:
        c = CalibrationConfig.load_defaults()
        assert c.max_file_size_bytes == 52_428_800
        assert c.stitch_min_relative_col_overlap == 0.75
        assert c.header_similarity_confirm == 0.85
        assert c.stitch_min_type_compatibility == 0.85

    def test_missing_yaml_raises_configuration_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigurationError, match="not found"):
            CalibrationConfig.from_yaml(missing)

    def test_malformed_yaml_raises_configuration_error(self, tmp_path: Path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{{{not: valid: yaml::::", encoding="utf-8")
        with pytest.raises(ConfigurationError, match="[Mm]alformed"):
            CalibrationConfig.from_yaml(bad_yaml)

    def test_empty_yaml_raises_configuration_error(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ConfigurationError, match="empty"):
            CalibrationConfig.from_yaml(empty)

    def test_invalid_threshold_range(self, tmp_path: Path) -> None:
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text(
            "stitch_min_relative_col_overlap: 2.5\n",  # > 1.0
            encoding="utf-8",
        )
        with pytest.raises(ConfigurationError, match="[Ii]nvalid"):
            CalibrationConfig.from_yaml(invalid_yaml)

    def test_negative_page_count_rejected(self, tmp_path: Path) -> None:
        invalid_yaml = tmp_path / "neg.yaml"
        invalid_yaml.write_text("max_pdf_pages: -5\n", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            CalibrationConfig.from_yaml(invalid_yaml)


# ── Path Independence ───────────────────────────────────────────────────────


class TestPathIndependence:
    """Verify config loads regardless of CWD."""

    def test_config_loads_from_different_cwd(self, tmp_path: Path) -> None:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            s = AppSettings()
            assert s.thresholds_path is not None
            assert s.thresholds_path.is_file()

            c = CalibrationConfig.load_defaults()
            assert c.max_file_size_bytes == 52_428_800
        finally:
            os.chdir(original_cwd)
