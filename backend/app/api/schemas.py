"""DocuStruct AI — API Response Schemas.

Pydantic v2 models for API-specific response types that are not
part of the core domain model (e.g., health check).

Domain models (DocumentEvaluationReport, CanonicalTable, etc.) are
defined in ``app.models.domain`` and re-used directly by endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for ``GET /api/v1/health``.

    Matches the ``HealthResponse`` contract in
    ``frontend/src/types/api.ts``.
    """

    status: str = "healthy"
    version: str = "1.0.0"
    backend_ready: bool = True
