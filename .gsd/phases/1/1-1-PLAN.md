---
phase: 1
plan: 1
wave: 1
depends_on: []
---

# Plan 1.1: Project Scaffolding & Configuration System

## Objective
Establish the backend package structure, packaging specifications (`pyproject.toml`, `requirements.txt`), and implement the typed configuration and calibration system (`settings.py`, `calibration.py`, `thresholds.yaml`) with path-independent loading and explicit units.

## Context
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-01, NFR-01, NFR-03, CON-01)
- `MASTER_DIRECTIVE.md` (Sections 3, 5, 6, 7)
- `.gsd/phases/1/RESEARCH.md`

## Tasks

<task type="auto">
  <name>Configure backend project packaging and dependency specifications</name>
  <files>
    backend/pyproject.toml
    backend/requirements.txt
    backend/app/__init__.py
    backend/app/config/__init__.py
  </files>
  <action>
    Create backend/requirements.txt containing strictly the 7 approved dependencies:
    - pydantic>=2.7,<3.0
    - pydantic-settings>=2.2
    - PyYAML>=6.0
    - PyMuPDF>=1.24.0
    - pdfplumber>=0.11.0
    - rapidfuzz>=3.9.0
    - pytest>=8.2.0

    Create backend/pyproject.toml configured for:
    - Python compatibility: `>=3.10,<3.13` (target 3.11).
    - Build system using setuptools.
    - Package discovery mapping `app` as package.
    - Pytest settings configured with testpaths = ["tests"] and pythonpath = ["."].

    Create app/__init__.py and app/config/__init__.py with clean exports and no side effects.
  </action>
  <verify>
    powershell -Command "Test-Path 'backend/pyproject.toml'; Test-Path 'backend/requirements.txt'; Select-String -Path 'backend/requirements.txt' -Pattern 'pydantic'"
  </verify>
  <done>
    `requirements.txt` lists exactly the 7 approved dependencies with zero unapproved packages; `pyproject.toml` is syntactically valid and specifies Python >=3.10,<3.13; package `__init__.py` files exist.
  </done>
</task>

<task type="auto">
  <name>Implement configuration settings, calibration loader, and thresholds YAML</name>
  <files>
    backend/app/config/settings.py
    backend/app/config/calibration.py
    backend/app/config/thresholds.yaml
  </files>
  <action>
    1. Create backend/app/config/thresholds.yaml:
       Define default thresholds with explicit units and comments noting they are starting defaults marked UNMEASURED:
       - max_file_size_bytes: 26214400 (25 MiB)
       - max_pdf_pages: 50
       - max_workers: 1
       - stitch_min_relative_col_overlap: 0.75
       - header_similarity_confirm: 0.85
       - stitch_min_type_compatibility: 0.85
       - page classification thresholds (char count, garbled ratio, image coverage).

    2. Create backend/app/config/settings.py:
       Implement AppSettings(BaseSettings) with Pydantic v2 SettingsConfigDict:
       - max_file_size_bytes: int = 26214400
       - max_pdf_pages: int = 50
       - max_workers: int = 1
       - workspace_root: Path (defaults to safe path under system temp or project dir)
       - enable_memory_measurement: bool = False
       - Path independence: resolve default paths relative to Path(__file__).resolve().

    3. Create backend/app/config/calibration.py:
       Implement CalibrationConfig(BaseModel) validated against thresholds.yaml:
       - Load yaml using yaml.safe_load.
       - Raise clear, typed ConfigurationError on missing or malformed YAML or invalid numeric ranges.
       - Do not silently replace malformed configuration with arbitrary defaults.
  </action>
  <verify>
    powershell -Command "python -c 'from app.config.settings import AppSettings; s = AppSettings(); print(s.max_file_size_bytes)'"
  </verify>
  <done>
    AppSettings and CalibrationConfig load and validate successfully regardless of CWD; malformed YAML raises explicit configuration errors; units are documented and explicit.
  </done>
</task>

## Success Criteria
- [ ] `backend/pyproject.toml` and `backend/requirements.txt` created with exact 7 approved dependencies.
- [ ] `backend/app/config/thresholds.yaml` created with centralized defaults and UNMEASURED disclaimer.
- [ ] `AppSettings` and `CalibrationConfig` implemented in `settings.py` and `calibration.py` with typed validation and path-independence.
- [ ] No circular imports or import side effects.
