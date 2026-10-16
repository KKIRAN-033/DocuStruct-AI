"""DocuStruct AI — Base Orchestration Worker.

Coordinates task prompt dispatching, execution chain resolution, provider adapter
retrieval, structured response validation, and bounded fallback management.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from app.llm.config import MultiLLMSettings
from app.llm.enums import TaskType
from app.llm.fallback import BoundedFallbackEngine, FallbackResult
from app.llm.models import CandidateModel, StructuredCompletionResponse
from app.llm.providers.factory import ProviderFactory
from app.llm.router import TaskRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseWorker:
    """Base class for multi-model orchestration workers."""

    def __init__(
        self,
        router: Optional[TaskRouter] = None,
        engine: Optional[BoundedFallbackEngine] = None,
        settings: Optional[MultiLLMSettings] = None,
    ) -> None:
        self._settings = settings or MultiLLMSettings()
        self._router = router or TaskRouter(settings=self._settings)
        self._engine = engine or BoundedFallbackEngine(max_fallbacks=2)

    @property
    def router(self) -> TaskRouter:
        """Return the TaskRouter instance."""
        return self._router

    @property
    def engine(self) -> BoundedFallbackEngine:
        """Return the BoundedFallbackEngine instance."""
        return self._engine

    async def execute_task(
        self,
        task: TaskType,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        requires_vision: bool = False,
        images: Optional[list[bytes]] = None,
    ) -> FallbackResult:
        """Resolve candidate chain and execute task with bounded fallbacks.

        If no candidates are eligible or all candidates fail, returns a FallbackResult
        with fallback_to_deterministic=True.
        """
        candidates = self._router.resolve_execution_chain(
            task=task,
            requires_vision=requires_vision,
        )

        async def _invoke_candidate(candidate: CandidateModel) -> T:
            adapter = ProviderFactory.get_adapter_for_model(
                candidate=candidate,
                settings=self._settings,
            )
            response: StructuredCompletionResponse = await adapter.complete_structured(
                prompt=prompt,
                model_id=candidate.exact_model_id,
                schema=response_model,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=1024,
                images=images,
            )
            return response.parsed

        return await self._engine.execute_with_fallback(
            task=task,
            candidates=candidates,
            invoke_fn=_invoke_candidate,
        )
