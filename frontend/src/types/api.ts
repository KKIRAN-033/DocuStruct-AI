/**
 * DocuStruct AI — Frontend HTTP API Type Contracts
 *
 * Defines request and response types for the minimal FastAPI adapter:
 *   - GET  /api/v1/health
 *   - GET  /api/v1/models/status
 *   - POST /api/v1/extract
 *   - POST /api/v1/export/csv
 *   - POST /api/v1/export/json
 */

import type { CanonicalTable, DocumentEvaluationReport } from './domain';

// ── Health Endpoint ──────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  backend_ready: boolean;
}

// ── Models Status Endpoint (Multi-LLM Architecture) ──────────────────────────

export type TaskType =
  | 'ROUTINE_CLASSIFICATION'
  | 'COMPLEX_TABLE_INTERPRETATION'
  | 'CONFLICTING_HYPOTHESES'
  | 'CORRECTION_PROPOSAL'
  | 'MULTILINGUAL_INTERPRETATION'
  | 'VISUAL_TABLE_REVIEW'
  | 'USER_EXPLANATION';

export type Modality = 'TEXT' | 'VISION';

export type ProviderType =
  | 'GROQ'
  | 'TOGETHER'
  | 'OPENROUTER'
  | 'DEEPSEEK'
  | 'ZAI';

export type ModelExistenceStatus = 'UNVERIFIED' | 'CONFIRMED' | 'UNAVAILABLE';

export type ProviderAvailabilityStatus = 'UNVERIFIED' | 'AVAILABLE' | 'UNAVAILABLE';

export type ConfigurationCredentialStatus = 'MISSING_CREDENTIALS' | 'CONFIGURED';

export type IntegrationTestStatus = 'UNTESTED' | 'PASSED' | 'FAILED';

export interface TimeoutRetryPolicy {
  timeout_seconds: number;
  max_retries: number;
  backoff_base_seconds: number;
}

export interface IntegrationTestRecord {
  status: IntegrationTestStatus;
  timestamp: string;
  latency_ms?: number;
  error_code?: string;
}

export interface ModelVerificationStatus {
  existence: ModelExistenceStatus;
  provider_availability: ProviderAvailabilityStatus;
  credentials: ConfigurationCredentialStatus;
  test_result: IntegrationTestStatus;
}

export interface CandidateModel {
  candidate_name: string;
  exact_model_id: string;
  provider: ProviderType;
  supported_modalities: Modality[];
  supported_tasks: TaskType[];
  configuration_key: string;
  enabled_state: boolean;
  verification_status: ModelVerificationStatus;
  routing_priority: number;
  timeout_retry_policy: TimeoutRetryPolicy;
  fallback_eligibility: boolean;
  last_integration_test_result?: IntegrationTestRecord | null;
}

export interface ProviderHealth {
  provider: ProviderType;
  available: boolean;
  configured: boolean;
  error_message?: string | null;
}

export interface ModelsStatusResponse {
  models: CandidateModel[];
  providers: Record<string, ProviderHealth>;
  timestamp: string;
}

// ── Extract Endpoint ─────────────────────────────────────────────────────────

export interface ExtractRequest {
  file: File;
}

export type ExtractResponse = DocumentEvaluationReport;

// ── Table Export Endpoints ───────────────────────────────────────────────────

export type ExportCsvRequest = CanonicalTable;

export type ExportJsonRequest = CanonicalTable;

export interface ExportJsonResponse {
  table_id: string;
  headers: string[];
  rows: string[][];
}

// ── Error Envelope ───────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status_code?: number;
  raw?: unknown;
}
