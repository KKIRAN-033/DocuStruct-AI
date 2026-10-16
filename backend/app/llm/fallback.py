"""DocuStruct AI — Bounded Fallback Engine & Cycle Detector.

Coordinates multi-model fallback execution with strict bounds (max_fallbacks=2),
cycle prevention, typed failure classification, and deterministic continuation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.llm.enums import ProviderType, TaskType
from app.llm.exceptions import (
    ModelNotFoundError,
    MultiLLMError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.models import CandidateModel

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Typed Reason Codes ───────────────────────────────────────────────────────
REASON_AUTH_ERROR = "AUTH_ERROR"
REASON_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
REASON_RATE_LIMIT = "RATE_LIMIT_EXCEEDED"
REASON_TIMEOUT = "TIMEOUT"
REASON_SCHEMA_ERROR = "SCHEMA_VALIDATION_ERROR"
REASON_SERVER_ERROR = "SERVER_ERROR"
REASON_CYCLE_PREVENTED = "CYCLE_PREVENTED"
REASON_MAX_FALLBACKS_EXCEEDED = "MAX_FALLBACKS_EXCEEDED"


class FallbackAttemptRecord(BaseModel):
    """Timestamped audit record of a candidate invocation attempt."""

    model_config = ConfigDict(protected_namespaces=())

    candidate_name: str
    provider: ProviderType
    model_id: str
    attempt_number: int
    success: bool
    error_reason: Optional[str] = None
    error_message: Optional[str] = None
    retry_after_seconds: Optional[float] = None
    latency_ms: float = 0.0


class FallbackResult(BaseModel):
    """Aggregate result of a bounded multi-model fallback execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    success: bool
    result: Any = None
    candidate_used: Optional[CandidateModel] = None
    fallback_hops: int = 0
    fallback_to_deterministic: bool = False
    audit_trail: list[FallbackAttemptRecord] = Field(default_factory=list)
    failure_summary: Optional[str] = None


class BoundedFallbackEngine:
    """Bounded fallback engine limiting retries to max_fallbacks=2 with cycle prevention."""

    def __init__(self, max_fallbacks: int = 2) -> None:
        if max_fallbacks < 0:
            raise ValueError("max_fallbacks must be non-negative")
        self.max_fallbacks = max_fallbacks

    async def execute_with_fallback(
        self,
        task: TaskType,
        candidates: list[CandidateModel],
        invoke_fn: Callable[[CandidateModel], Awaitable[T]],
    ) -> FallbackResult:
        """Execute a task through an ordered candidate chain with bounded fallbacks.

        Enforces:
            1. Total attempts capped at (max_fallbacks + 1).
            2. Cycle prevention: a candidate cannot be invoked more than once.
            3. Detailed failure reason categorization for audit trails.
            4. Unconditional fallback_to_deterministic=True when all candidates fail.
            5. Strict invariant: never reports success=True unless an eligible model succeeds.
        """
        if not candidates:
            logger.info("Fallback engine received zero candidates. Defaulting to deterministic.")
            return FallbackResult(
                success=False,
                fallback_to_deterministic=True,
                audit_trail=[],
                failure_summary="No eligible candidates available for invocation.",
            )

        visited_candidates: set[str] = set()
        audit_trail: list[FallbackAttemptRecord] = []
        fallback_hops = 0
        attempt_count = 0
        max_attempts = self.max_fallbacks + 1

        for candidate in candidates:
            # 1. Check max attempts ceiling
            if attempt_count >= max_attempts:
                logger.warning(
                    "Exceeded maximum fallback attempts (%d). Stopping execution chain.",
                    max_attempts,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count + 1,
                        success=False,
                        error_reason=REASON_MAX_FALLBACKS_EXCEEDED,
                        error_message=f"Halt: reached max_fallbacks limit of {self.max_fallbacks}",
                    )
                )
                break

            # 2. Cycle prevention
            if candidate.candidate_name in visited_candidates:
                logger.warning(
                    "Routing cycle detected for candidate '%s'. Skipping duplicate attempt.",
                    candidate.candidate_name,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count + 1,
                        success=False,
                        error_reason=REASON_CYCLE_PREVENTED,
                        error_message="Candidate already attempted in this request chain",
                    )
                )
                continue

            visited_candidates.add(candidate.candidate_name)
            attempt_count += 1
            start_time = time.perf_counter()

            try:
                logger.debug(
                    "Invoking candidate '%s' (attempt %d/%d) for task %s",
                    candidate.candidate_name,
                    attempt_count,
                    max_attempts,
                    task.value,
                )
                result = await invoke_fn(candidate)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=True,
                        latency_ms=elapsed_ms,
                    )
                )

                return FallbackResult(
                    success=True,
                    result=result,
                    candidate_used=candidate,
                    fallback_hops=fallback_hops,
                    fallback_to_deterministic=False,
                    audit_trail=audit_trail,
                )

            except ProviderAuthError as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Candidate '%s' failed authentication (non-retryable on this provider): %s",
                    candidate.candidate_name,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_AUTH_ERROR,
                        error_message=str(exc),
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

            except (ProviderServiceUnavailableError, ModelNotFoundError) as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Candidate '%s' unavailable or model not found: %s",
                    candidate.candidate_name,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_UNAVAILABLE,
                        error_message=str(exc),
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

            except RateLimitExceededError as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Candidate '%s' rate limited (retry_after=%s): %s",
                    candidate.candidate_name,
                    exc.retry_after_seconds,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_RATE_LIMIT,
                        error_message=str(exc),
                        retry_after_seconds=exc.retry_after_seconds,
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

            except (ProviderTimeoutError, asyncio.TimeoutError, TimeoutError) as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Candidate '%s' timed out after %.2f ms: %s",
                    candidate.candidate_name,
                    elapsed_ms,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_TIMEOUT,
                        error_message=str(exc),
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

            except SchemaValidationError as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Candidate '%s' returned invalid structured schema: %s",
                    candidate.candidate_name,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_SCHEMA_ERROR,
                        error_message=str(exc),
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

            except (MultiLLMError, Exception) as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.error(
                    "Candidate '%s' encountered server or unhandled error: %s",
                    candidate.candidate_name,
                    exc,
                )
                audit_trail.append(
                    FallbackAttemptRecord(
                        candidate_name=candidate.candidate_name,
                        provider=candidate.provider,
                        model_id=candidate.exact_model_id,
                        attempt_number=attempt_count,
                        success=False,
                        error_reason=REASON_SERVER_ERROR,
                        error_message=str(exc),
                        latency_ms=elapsed_ms,
                    )
                )
                fallback_hops += 1

        summary = (
            f"All {len(visited_candidates)} candidate attempts failed or exhausted. "
            f"Fallback hops: {fallback_hops}. Triggering deterministic continuation."
        )
        logger.info(summary)

        return FallbackResult(
            success=False,
            result=None,
            candidate_used=None,
            fallback_hops=fallback_hops,
            fallback_to_deterministic=True,
            audit_trail=audit_trail,
            failure_summary=summary,
        )
