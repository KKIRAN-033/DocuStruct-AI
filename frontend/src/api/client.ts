/**
 * DocuStruct AI — Typed HTTP API Client
 *
 * Exclusively integrates existing FastAPI backend endpoints:
 *   - GET  /api/v1/health
 *   - GET  /api/v1/models/status
 *   - POST /api/v1/extract
 *   - POST /api/v1/export/csv
 *   - POST /api/v1/export/json
 *
 * Invariants:
 *   - Zero invented backend routes.
 *   - Zero hardcoded API keys or browser-side LLM direct calls.
 *   - Respects 25 MiB upload ceiling with client pre-flight check.
 *   - Normalizes network timeouts and server disconnects into typed ApiError.
 */

import type {
  ApiError,
  HealthResponse,
  ModelsStatusResponse,
  ExtractResponse,
} from '../types/api';
import type { CanonicalTable } from '../types/domain';

export const MAX_FILE_SIZE_BYTES = 52_428_800; // 50 MiB

export class ApiClient {
  private baseUrl: string;
  private defaultTimeoutMs: number;

  constructor(
    baseUrl: string = import.meta.env.VITE_API_BASE_URL || '',
    defaultTimeoutMs: number = 60_000
  ) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  /**
   * Helper executing fetch with AbortSignal timeout and typed error normalization.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs?: number
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const timeout = timeoutMs ?? this.defaultTimeoutMs;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      if (!response.ok) {
        let detail = `Request failed with HTTP ${response.status}`;
        let raw: unknown = null;
        try {
          const body = await response.json();
          raw = body;
          if (body && typeof body === 'object' && 'detail' in body) {
            detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          const text = await response.text().catch(() => '');
          if (text) detail = text;
        }

        const err: ApiError = {
          detail,
          status_code: response.status,
          raw,
        };
        throw err;
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'status_code' in err) {
        throw err as ApiError;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        const timeoutErr: ApiError = {
          detail: `Request timed out after ${timeout / 1000}s. Please check backend responsiveness.`,
          status_code: 408,
        };
        throw timeoutErr;
      }

      const networkErr: ApiError = {
        detail:
          err instanceof Error
            ? `Backend unreachable: ${err.message}. Verify that FastAPI is running on port 8000.`
            : 'Unknown network communication failure.',
        status_code: 0,
        raw: err,
      };
      throw networkErr;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * GET /api/v1/health
   */
  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/health', {
      method: 'GET',
    }, 5_000);
  }

  /**
   * GET /api/v1/models/status
   */
  async getModelsStatus(): Promise<ModelsStatusResponse> {
    return this.request<ModelsStatusResponse>('/api/v1/models/status', {
      method: 'GET',
    }, 10_000);
  }

  /**
   * POST /api/v1/extract
   * Sends multipart/form-data with 25 MiB preflight validation and default 120s timeout.
   */
  async extractDocument(
    file: File,
    signal?: AbortSignal,
    timeoutMs: number = 120_000
  ): Promise<ExtractResponse> {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const err: ApiError = {
        detail: `File size (${(file.size / (1024 * 1024)).toFixed(1)} MiB) exceeds the 50 MiB operational limit.`,
        status_code: 413,
      };
      throw err;
    }

    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/api/v1/extract`;
    const controller = new AbortController();
    let isTimedOut = false;
    const timeoutId = setTimeout(() => {
      isTimedOut = true;
      controller.abort();
    }, timeoutMs);

    const onCallerAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) {
        clearTimeout(timeoutId);
        const err: ApiError = {
          detail: 'Extraction cancelled by user.',
          status_code: 499,
        };
        throw err;
      }
      signal.addEventListener('abort', onCallerAbort, { once: true });
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        let detail = `Extraction failed with HTTP ${response.status}`;
        try {
          const body = await response.json();
          if (body && typeof body === 'object' && 'detail' in body) {
            detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          const text = await response.text().catch(() => '');
          if (text) detail = text;
        }
        const err: ApiError = {
          detail,
          status_code: response.status,
        };
        throw err;
      }

      return (await response.json()) as ExtractResponse;
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'status_code' in err) {
        throw err as ApiError;
      }

      if (isTimedOut) {
        const timeoutErr: ApiError = {
          detail: `Extraction timed out after ${timeoutMs / 1000}s. Processing complex documents may require higher timeout.`,
          status_code: 408,
        };
        throw timeoutErr;
      }

      if (signal?.aborted) {
        const cancelErr: ApiError = {
          detail: 'Extraction cancelled by user.',
          status_code: 499,
        };
        throw cancelErr;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        const cancelErr: ApiError = {
          detail: 'Extraction request was aborted.',
          status_code: 499,
        };
        throw cancelErr;
      }

      const networkErr: ApiError = {
        detail:
          err instanceof Error
            ? `Extraction failed: ${err.message}. Verify that FastAPI is running on port 8000.`
            : 'Unknown network failure during extraction.',
        status_code: 0,
        raw: err,
      };
      throw networkErr;
    } finally {
      clearTimeout(timeoutId);
      if (signal) {
        signal.removeEventListener('abort', onCallerAbort);
      }
    }
  }

  /**
   * POST /api/v1/export/csv
   * Returns Blob for client-side download.
   */
  async exportCsv(table: CanonicalTable): Promise<Blob> {
    const url = `${this.baseUrl}/api/v1/export/csv`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(table),
    });

    if (!response.ok) {
      throw new Error(`CSV export failed with HTTP ${response.status}`);
    }
    return response.blob();
  }

  /**
   * POST /api/v1/export/json
   * Returns Blob for client-side download.
   */
  async exportJson(table: CanonicalTable): Promise<Blob> {
    const url = `${this.baseUrl}/api/v1/export/json`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(table),
    });

    if (!response.ok) {
      throw new Error(`JSON export failed with HTTP ${response.status}`);
    }
    return response.blob();
  }

  /**
   * POST /api/v1/export/zip
   * Returns Blob for client-side download of all tables in a zip archive.
   */
  async exportZip(tables: CanonicalTable[]): Promise<Blob> {
    const url = `${this.baseUrl}/api/v1/export/zip`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tables),
    });

    if (!response.ok) {
      throw new Error(`ZIP export failed with HTTP ${response.status}`);
    }
    return response.blob();
  }
}

export const apiClient = new ApiClient();
