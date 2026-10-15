"""
DocuStruct AI — Backend Application Package

Deterministic document table extraction and verification system.
Phase 1: Digital PDF table extraction with arithmetic consistency
verification and quality gates.
"""

__version__ = "0.1.0"

from app.pipeline import run_phase1_pipeline

__all__ = ["run_phase1_pipeline", "__version__"]
