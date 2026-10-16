"""DocuStruct AI — Multi-LLM Orchestration Workers Package.

Contains specialized workers for evidence-gated cell corrections, conflict adjudication,
and user-facing explanations, all backed by strict Pydantic schemas and deterministic fallback.
"""

from app.llm.workers.base_worker import BaseWorker
from app.llm.workers.correction_worker import CorrectionWorker
from app.llm.workers.discrepancy_worker import DiscrepancyWorker
from app.llm.workers.explanation_worker import ExplanationWorker

__all__ = [
    "BaseWorker",
    "CorrectionWorker",
    "DiscrepancyWorker",
    "ExplanationWorker",
]
