import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient, MAX_FILE_SIZE_BYTES } from '../client';
import type { CanonicalTable } from '../../types/domain';
import type { ModelsStatusResponse } from '../../types/api';

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient('http://test-server:8000');
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('checks health successfully on GET /api/v1/health', async () => {
    const mockHealth = { status: 'healthy', version: '1.0.0', backend_ready: true };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const res = await client.checkHealth();
    expect(res).toEqual(mockHealth);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-server:8000/api/v1/health',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('retrieves model registry status on GET /api/v1/models/status', async () => {
    const mockStatus: ModelsStatusResponse = {
      models: [
        {
          candidate_name: 'GPT-OSS 20B',
          exact_model_id: 'UNVERIFIED',
          provider: 'GROQ',
          supported_modalities: ['TEXT'],
          supported_tasks: ['ROUTINE_CLASSIFICATION'],
          configuration_key: 'DOCUSTRUCT_MODEL_GPT_OSS_20B_ID',
          enabled_state: false,
          verification_status: {
            existence: 'UNVERIFIED',
            provider_availability: 'UNVERIFIED',
            credentials: 'MISSING_CREDENTIALS',
            test_result: 'UNTESTED',
          },
          routing_priority: 1,
          timeout_retry_policy: { timeout_seconds: 15.0, max_retries: 2, backoff_base_seconds: 1.5 },
          fallback_eligibility: true,
        },
      ],
      providers: {
        GROQ: { provider: 'GROQ', available: false, configured: false },
      },
      timestamp: '2026-10-15T20:00:00Z',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    } as Response);

    const res = await client.getModelsStatus();
    expect(res.models).toHaveLength(1);
    expect(res.models[0].candidate_name).toBe('GPT-OSS 20B');
    expect(res.models[0].enabled_state).toBe(false);
  });

  it('rejects oversized file preflight on POST /api/v1/extract without network call', async () => {
    const oversizedFile = new File(['x'.repeat(100)], 'huge.pdf', { type: 'application/pdf' });
    Object.defineProperty(oversizedFile, 'size', { value: MAX_FILE_SIZE_BYTES + 1 });

    global.fetch = vi.fn();

    await expect(client.extractDocument(oversizedFile)).rejects.toMatchObject({
      status_code: 413,
      detail: expect.stringContaining('exceeds the 50 MiB operational limit'),
    });

    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('extracts valid PDF successfully via POST /api/v1/extract', async () => {
    const validFile = new File(['%PDF-1.4 sample content'], 'invoice.pdf', {
      type: 'application/pdf',
    });

    const mockReport = {
      job_id: 'job_123',
      filename: 'invoice.pdf',
      execution_state: 'COMPLETED',
      verification_status: 'VERIFIED',
      canonical_tables: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockReport,
    } as Response);

    const res = await client.extractDocument(validFile);
    expect(res).toEqual(mockReport);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-server:8000/api/v1/extract',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) })
    );
  });

  it('normalizes HTTP 500 error into typed ApiError with detail', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal Pipeline Error' }),
    } as Response);

    await expect(client.checkHealth()).rejects.toMatchObject({
      status_code: 500,
      detail: 'Internal Pipeline Error',
    });
  });

  it('normalizes network disconnect into typed ApiError with status_code 0', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(client.checkHealth()).rejects.toMatchObject({
      status_code: 0,
      detail: expect.stringContaining('Backend unreachable'),
    });
  });

  it('exports CSV as a Blob via POST /api/v1/export/csv', async () => {
    const mockBlob = new Blob(['ColA,ColB\n1,2'], { type: 'text/csv' });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => mockBlob,
    } as Response);

    const mockTable = { table_id: 'tbl_1', rows: [] } as unknown as CanonicalTable;
    const blob = await client.exportCsv(mockTable);
    expect(blob).toBe(mockBlob);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-server:8000/api/v1/export/csv',
      expect.objectContaining({ method: 'POST' })
    );
  });
});
