# DocuStruct AI — Multi-LLM Architecture Specification & Operational Guide

## 1. System Overview

DocuStruct AI incorporates a provider-agnostic, multi-model intelligence subsystem to augment deterministic document extraction with advisory AI capabilities. Built on **DECISION-010** and **DECISION-011**, the architecture enforces four foundational guarantees:

1. **Deterministic Authority**: The deterministic extraction, normalization, verification, and quality-gate engine is 100% authoritative. AI models act as advisory candidate generators and cannot bypass security limits, file boundaries, or mathematical quality gates.
2. **Raw Value Immutability**: `cell.raw_value` is immutable across all extraction, normalisation, and AI suggestion workflows.
3. **Prohibition of Auto-Balancing**: AI models are strictly forbidden from altering cell values to force mathematical balance (e.g., $100 + $200 = $350 preserves printed $350 and reports a discrepancy; DECISION-007).
4. **Zero Vendor Lock-In**: Standard asynchronous HTTP (`httpx`) adapters decouple the application from third-party vendor SDKs.

---

## 2. The Seven Candidate Models

All candidates are declaratively registered in `backend/app/llm/registry.py` with explicit 12-field schemas. Initial exact model IDs default to `"UNVERIFIED"`, `enabled_state = False`, and `test_result = UNTESTED`.

| # | Candidate Name | Provider | Default Modality | Supported Tasks | Config Key |
|---|---|---|---|---|---|
| 1 | **GPT-OSS 20B** | Groq | TEXT | `ROUTINE_CLASSIFICATION`, `CORRECTION_PROPOSAL`, `USER_EXPLANATION` | `DOCUSTRUCT_MODEL_GPT_OSS_20B_ID` |
| 2 | **GPT-OSS 120B** | Together AI | TEXT | `COMPLEX_TABLE_INTERPRETATION`, `CONFLICTING_HYPOTHESES` | `DOCUSTRUCT_MODEL_GPT_OSS_120B_ID` |
| 3 | **DeepSeek V4.1 Flash** | DeepSeek API | TEXT | `COMPLEX_TABLE_INTERPRETATION`, `CORRECTION_PROPOSAL`, `ROUTINE_CLASSIFICATION` | `DOCUSTRUCT_MODEL_DEEPSEEK_V4_1_FLASH_ID` |
| 4 | **GLM-5.3-Flash through Z.ai** | Z.ai API | TEXT | `COMPLEX_TABLE_INTERPRETATION`, `CONFLICTING_HYPOTHESES` | `DOCUSTRUCT_MODEL_GLM_5_3_FLASH_ID` |
| 5 | **Qwen3.8-27B** | Together AI | TEXT (Vision unverified) | `MULTILINGUAL_INTERPRETATION`, `VISUAL_TABLE_REVIEW` | `DOCUSTRUCT_MODEL_QWEN_3_8_27B_ID` |
| 6 | **Llama 4 Scout** | Groq | TEXT (Vision unverified) | `VISUAL_TABLE_REVIEW`, `ROUTINE_CLASSIFICATION` | `DOCUSTRUCT_MODEL_LLAMA_4_SCOUT_ID` |
| 7 | **Gemma 4** | Groq | TEXT (Vision unverified) | `VISUAL_TABLE_REVIEW`, `ROUTINE_CLASSIFICATION` | `DOCUSTRUCT_MODEL_GEMMA_4_ID` |

*Note: Models supporting visual tasks require empirical confirmation of `Modality.VISION` before being eligible for `VISUAL_TABLE_REVIEW`.*

---

## 3. The Five Provider Adapters

All provider adapters inherit from `BaseProviderAdapter` (`backend/app/llm/providers/base.py`) and implement asynchronous HTTP communication via `httpx`:

1. **Groq (`GroqProviderAdapter`)**: Low-latency inference at `https://api.groq.com/openai/v1`. Parses `Retry-After` headers on HTTP 429.
2. **Together AI (`TogetherProviderAdapter`)**: Open-weight inference at `https://api.together.xyz/v1`.
3. **OpenRouter (`OpenRouterProviderAdapter`)**: Aggregated multi-model routing at `https://openrouter.ai/api/v1` with mandatory attribution headers: `HTTP-Referer: https://docustruct.ai` and `X-Title: DocuStruct AI`.
4. **DeepSeek API (`DeepSeekProviderAdapter`)**: DeepSeek endpoint at `https://api.deepseek.com/v1`.
5. **Z.ai API (`ZaiProviderAdapter`)**: Z.ai GLM endpoint at `https://api.z.ai/v1`.

### Centralized ProviderFactory
Adapters are managed and cached via `ProviderFactory` (`backend/app/llm/providers/factory.py`). To prevent stale configurations when settings change, the cache key comprises `(provider_type, api_key, base_url, timeout)`.

---

## 4. TaskRouter & Pre-Flight Eligibility Gate

The `TaskRouter` (`backend/app/llm/router.py`) maps seven discrete task types to candidate preference chains:

```python
TASK_CANDIDATE_PREFERENCES = {
    TaskType.ROUTINE_CLASSIFICATION: ["GPT-OSS 20B", "DeepSeek V4.1 Flash", "Llama 4 Scout"],
    TaskType.COMPLEX_TABLE_INTERPRETATION: ["DeepSeek V4.1 Flash", "GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"],
    TaskType.CONFLICTING_HYPOTHESES: ["GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"],
    TaskType.CORRECTION_PROPOSAL: ["GPT-OSS 20B", "DeepSeek V4.1 Flash"],
    TaskType.MULTILINGUAL_INTERPRETATION: ["Qwen3.8-27B"],
    TaskType.VISUAL_TABLE_REVIEW: ["Qwen3.8-27B", "Llama 4 Scout", "Gemma 4"],
    TaskType.USER_EXPLANATION: ["GPT-OSS 20B"],
}
```

### 8-Point Pre-Flight Eligibility Check
Before a candidate can be scheduled in an execution chain, `evaluate_candidate_eligibility` verifies:
1. `enabled_state is True` (disabled models rejected).
2. `exact_model_id != "UNVERIFIED"` and non-empty.
3. `credentials == CONFIGURED` (missing provider keys rejected).
4. `existence == CONFIRMED` (model ID physically verified on endpoint).
5. `provider_availability == AVAILABLE` (endpoint reachable).
6. `test_result == PASSED` (automated probe succeeded).
7. `task in candidate.supported_tasks` (task affinity supported).
8. `Modality.VISION in candidate.supported_modalities` for vision tasks.

If no candidates satisfy all 8 conditions, `resolve_execution_chain` returns `[]`, triggering **deterministic continuation** without making network requests.

---

## 5. Bounded Fallback Engine & Cycle Prevention

The `BoundedFallbackEngine` (`backend/app/llm/fallback.py`) manages multi-model execution:
- **Ceiling**: `max_fallbacks = 2` limits total invocations to at most 3 attempts (1 primary + 2 fallbacks).
- **Cycle Prevention**: Tracks `visited_candidates: set[str]`. Duplicate candidate IDs in a chain are skipped with reason code `CYCLE_PREVENTED`.
- **Error Reason Taxonomy**: Classifies failures into `AUTH_ERROR`, `PROVIDER_UNAVAILABLE`, `RATE_LIMIT_EXCEEDED`, `TIMEOUT`, `SCHEMA_VALIDATION_ERROR`, and `SERVER_ERROR`.
- **Deterministic Hand-Off**: If all attempts fail, returns `FallbackResult(success=False, fallback_to_deterministic=True)`.

---

## 6. Structured Output Schemas & Evidence Gating

All multi-model outputs use strict Pydantic v2 models with `extra="forbid"` (`backend/app/llm/schemas.py`):
- `PageClassificationEnrichment`
- `TableInterpretationResult`
- `DiscrepancyHypothesis`
- `CorrectionProposal`
- `UserExplanationPayload`
- `ModelsStatusResponse`

### Evidence Gating Rules (`CorrectionWorker`)
- **Raw Value Protection**: `cell.raw_value` is never modified.
- **Prohibition of Auto-Balancing**: If the target cell is a total or sum, any proposal to force math consistency is strictly rejected (`REJECTED_AUTO_BALANCE_PRESERVED_RAW`). The proposal is stored only in `inferred_candidate_value` with `CellQualityStatus.ILLEGIBLE_OR_MISSING` and flagged for human review.
- **Permitted Evidence Allowlist**:
  - `NATIVE_PDF_CHAR_STREAM`
  - `INDEPENDENT_WORD_COORDINATES`
  - `VECTOR_GRID_GEOMETRY`
  Proposals backed by unapproved sources (`LLM_GUESS`, `HEURISTIC`, `WEB_SEARCH`) cannot alter `accepted_value`.
- **Deterministic Re-Validation**: Any accepted correction immediately triggers `evaluate_table_arithmetic_consistency` to verify internal table consistency.

---

## 7. Status Endpoint (`GET /api/v1/models/status`)

Exposed on the FastAPI adapter (`backend/app/api/app.py`):
- Returns HTTP 200 with `ModelsStatusResponse`.
- Fast and read-only: does not trigger slow network calls or reachability probes.
- Truthful reporting: unverified candidates report `enabled_state = False` and `test_result = UNTESTED`.
- Secret redaction: API keys, bearer tokens, and secrets are never exposed in JSON responses.

---

## 8. Testing Guide

### Running Mocked Unit & Integration Tests (Default)
All standard tests use 100% mocked HTTP via `respx` and run without real API keys:

```bash
# Run all backend tests (Phase 1–5 core, Phase 7 API, and Phase 8–11 LLM tests)
python -m pytest backend/tests -q

# Run Phase 11 integration test suite
python -m pytest backend/tests/llm backend/tests/api/test_models_status_api.py -v
```

### Opting Into Genuine Live Provider Integration Tests
Live provider tests make actual external HTTP requests. They are marked with `@pytest.mark.live` and skipped by default.

To run live integration tests:
1. Export the opt-in flag:
   ```bash
   # Windows PowerShell
   $env:DOCUSTRUCT_RUN_LIVE_TESTS = "1"
   ```
2. Export your provider API key(s):
   ```bash
   $env:GROQ_API_KEY = "gsk_..."
   $env:TOGETHER_API_KEY = "..."
   $env:OPENROUTER_API_KEY = "sk-or-..."
   $env:DEEPSEEK_API_KEY = "sk-..."
   $env:ZAI_API_KEY = "..."
   ```
3. Run with pytest:
   ```bash
   python -m pytest backend/tests/llm/test_provider_adapters.py -m live -v
   ```

When live credentials or the opt-in flag are absent, the test suite skips live tests safely.

---

## 9. Frontend Integration & Truthful UI Controls (Phase 13 & 14)

The editorial workstation (`frontend/`) integrates directly with the Multi-LLM architecture under strict truthfulness invariants:

1. **Model Registry Drawer (`ModelRegistryDrawer.tsx`)**:
   - Displays all 7 registered AI candidates and their 4-part verification statuses (`existence`, `availability`, `credentials`, `test_result`).
   - Displays live provider adapter latency and connectivity.
   - Prominently displays the architectural invariant disclaimer:
     > *"All 7 candidate models currently remain disabled, unverified, and non-operational. The deterministic extraction pipeline and arithmetic verification gates are 100% authoritative. No model outputs can mutate immutable source `raw_value` strings or auto-balance printed arithmetic totals."*

2. **Candidate Proposal Review Drawer (`CandidateProposalDrawer.tsx`)**:
   - Surfaces evidence-gated proposals from `cell.inferred_candidate_value` and table `correction_records`.
   - **Auto-Balancing Prohibition**: If target cell resides in a total or summary row (or was flagged as an auto-balance candidate), proposal acceptance is hard-blocked (`Accept Blocked (Total Row)`) with a warning callout citing DECISION-007 and DECISION-011.
   - On human acceptance for valid non-total cells: updates `cell.accepted_value` in local session React state; `cell.raw_value` remains strictly uncorrupted. Zero server persistence endpoints are invoked.

3. **Discrepancy Adjudication (`DiscrepancyAdjudication.tsx`)**:
   - Details arithmetic discrepancies between printed totals and calculated column sums.
   - Truthfully presents AI status as standby/unverified, providing deterministic rule explanations without fabricating fake LLM reasoning.
