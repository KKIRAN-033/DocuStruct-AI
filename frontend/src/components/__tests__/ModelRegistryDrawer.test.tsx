import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ModelRegistryDrawer } from '../layout/ModelRegistryDrawer';
import { apiClient } from '../../api/client';
import type { ModelsStatusResponse } from '../../types/api';

const mockResponse: ModelsStatusResponse = {
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
    {
      candidate_name: 'GPT-OSS 120B',
      exact_model_id: 'UNVERIFIED',
      provider: 'TOGETHER',
      supported_modalities: ['TEXT'],
      supported_tasks: ['COMPLEX_TABLE_INTERPRETATION'],
      configuration_key: 'DOCUSTRUCT_MODEL_GPT_OSS_120B_ID',
      enabled_state: false,
      verification_status: {
        existence: 'UNVERIFIED',
        provider_availability: 'UNVERIFIED',
        credentials: 'MISSING_CREDENTIALS',
        test_result: 'UNTESTED',
      },
      routing_priority: 1,
      timeout_retry_policy: { timeout_seconds: 45.0, max_retries: 2, backoff_base_seconds: 2.0 },
      fallback_eligibility: true,
    },
  ],
  providers: {
    GROQ: { provider: 'GROQ', available: false, configured: false },
    TOGETHER: { provider: 'TOGETHER', available: false, configured: false },
  },
  timestamp: '2026-10-15T21:00:00Z',
};

describe('ModelRegistryDrawer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders truthful disclaimer and models on open', async () => {
    vi.spyOn(apiClient, 'getModelsStatus').mockResolvedValue(mockResponse);

    render(<ModelRegistryDrawer isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText(/Multi-LLM Registry & Provider Health/i)).toBeInTheDocument();
    expect(
      screen.getByText(/All 7 candidate models currently remain/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('GPT-OSS 20B')).toBeInTheDocument();
      expect(screen.getByText('GPT-OSS 120B')).toBeInTheDocument();
    });

    const standbyBadges = screen.getAllByText('Disabled / Standby');
    expect(standbyBadges.length).toBeGreaterThanOrEqual(2);
  });
});
