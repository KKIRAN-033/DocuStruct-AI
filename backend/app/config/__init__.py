"""
DocuStruct AI — Configuration Package

Provides:
    - AppSettings: Typed application settings via pydantic-settings.
    - CalibrationConfig: Threshold calibration loaded from thresholds.yaml.
"""

from app.config.settings import AppSettings
from app.config.calibration import CalibrationConfig

__all__ = ["AppSettings", "CalibrationConfig"]
