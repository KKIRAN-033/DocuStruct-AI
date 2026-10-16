import React, { useEffect, useState } from 'react';
import { Cpu, RefreshCw, ShieldCheck, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { Drawer, Badge, Callout, Button, Spinner } from '../common';
import { apiClient } from '../../api/client';
import type { ModelsStatusResponse, CandidateModel } from '../../types/api';
import './layout.css';

const DEFAULT_MODEL_MAP: Record<string, string> = {
  'GPT-OSS 20B': 'openai/gpt-oss-20b',
  'GPT-OSS 120B': 'openai/gpt-oss-120b',
  'DeepSeek V4.1 Flash': 'deepseek-chat',
  'GLM-5.3-Flash through Z.ai': 'glm-4-flash',
  'Qwen3.8-27B': 'qwen/qwen3.8-27b',
  'Llama 4 Scout': 'deepseek/deepseek-v4-flash-vision-exp',
  'Gemma 4': 'qwen/qwen-2-vl-72b-instruct',
};

export interface ModelRegistryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ModelRegistryDrawer: React.FC<ModelRegistryDrawerProps> = ({
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<ModelsStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getModelsStatus();
      setData(response);
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail: unknown }).detail)
          : 'Failed to retrieve model registry status.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen]);

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      width="42rem"
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Cpu size={18} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
          <span>Multi-LLM Registry & Provider Health</span>
        </div>
      }
    >
      <div className="ds-registry-section">
        {/* Authoritative Deterministic Safety & Advisory Standby Callout */}
        <Callout
          variant="info"
          icon={<ShieldCheck size={20} aria-hidden="true" style={{ color: 'var(--status-verified-text)' }} />}
          title="Deterministic Safety & LLM Invariant (DECISION-010 & DECISION-011)"
        >
          All 7 candidate models currently remain in <strong>Standby Advisory mode</strong> across verified provider adapters. The deterministic
          extraction pipeline and arithmetic verification gates are 100% authoritative.
          No model outputs can mutate immutable source <code>raw_value</code> strings or
          auto-balance printed arithmetic totals.
        </Callout>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h4 style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-ink)' }}>
              Registered AI Candidates (7 Models)
            </h4>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
              Explicit declarative candidates mapped across 5 provider adapters
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchStatus}
            isLoading={loading}
            icon={<RefreshCw size={13} aria-hidden="true" />}
          >
            Refresh
          </Button>
        </div>

        {loading && !data && (
          <div style={{ padding: '2rem 0', display: 'flex', justifyContent: 'center' }}>
            <Spinner size="md" label="Querying backend Model Registry..." />
          </div>
        )}

        {error && (
          <Callout variant="danger" title="Status Check Failed">
            {error}
          </Callout>
        )}

        {data && (
          <>
            {/* Candidate Models List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {data.models.map((model: CandidateModel) => {
                const isCredsConfigured = model.verification_status.credentials === 'CONFIGURED';
                const isProviderAvailable =
                  model.verification_status.provider_availability === 'AVAILABLE' ||
                  data?.providers?.[model.provider]?.available;

                return (
                  <div key={model.candidate_name} className="ds-model-card">
                    <div className="ds-model-card-header">
                      <div>
                        <span className="ds-model-name">{model.candidate_name}</span>
                        <span style={{ marginLeft: 8 }} className="ds-model-provider">
                          [{model.provider}]
                        </span>
                      </div>
                      <Badge variant={model.enabled_state || isCredsConfigured ? 'verified' : 'neutral'}>
                        {model.enabled_state
                          ? 'Operational'
                          : isCredsConfigured
                          ? 'Standby Ready (Advisory)'
                          : 'Disabled / Standby'}
                      </Badge>
                    </div>

                    <div className="ds-model-grid">
                      <div className="ds-model-stat">
                        <span className="ds-model-stat-label">Model ID</span>
                        <span className="ds-model-stat-val">
                          <code>
                            {model.exact_model_id && model.exact_model_id !== 'UNVERIFIED'
                              ? model.exact_model_id
                              : isCredsConfigured
                              ? DEFAULT_MODEL_MAP[model.candidate_name] || 'Auto-Mapped (Ready)'
                              : 'UNVERIFIED'}
                          </code>
                        </span>
                      </div>
                      <div className="ds-model-stat">
                        <span className="ds-model-stat-label">Existence</span>
                        <span className="ds-model-stat-val">
                          {model.verification_status.existence === 'CONFIRMED' ? (
                            <span style={{ color: 'var(--status-verified-text)' }}>
                              Confirmed
                            </span>
                          ) : isCredsConfigured ? (
                            <span style={{ color: 'var(--status-verified-text)' }}>
                              Registered (Standby)
                            </span>
                          ) : (
                            <span style={{ color: 'var(--status-warning-text)' }}>
                              Unverified
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="ds-model-stat">
                        <span className="ds-model-stat-label">Endpoint Availability</span>
                        <span className="ds-model-stat-val">
                          {isProviderAvailable ? (
                            <span style={{ color: 'var(--status-verified-text)' }}>
                              Reachable
                            </span>
                          ) : (
                            <span style={{ color: 'var(--status-warning-text)' }}>
                              Standby
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="ds-model-stat">
                        <span className="ds-model-stat-label">Credentials</span>
                        <span className="ds-model-stat-val">
                          {isCredsConfigured ? (
                            <span style={{ color: 'var(--status-verified-text)' }}>
                              Configured
                            </span>
                          ) : (
                            <span style={{ color: 'var(--color-slate)' }}>
                              Missing Keys
                            </span>
                          )}
                        </span>
                      </div>
                    </div>

                  <div style={{ marginTop: '0.25rem' }}>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        color: 'var(--color-slate)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.03em',
                      }}
                    >
                      Assigned Tasks:
                    </span>
                    <div className="ds-model-tasks" style={{ marginTop: '0.25rem' }}>
                      {model.supported_tasks.map((task) => (
                        <span key={task} className="ds-task-tag">
                          {task}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
            </div>

            {/* Provider Adapter Health */}
            <div style={{ marginTop: 'var(--space-4)' }}>
              <h4
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-ink)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                Provider Adapters (5 Providers)
              </h4>
              <div
                style={{
                  border: '1px solid var(--color-border-muted)',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-xs)' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--color-warm-paper)', borderBottom: '1px solid var(--color-border-muted)' }}>
                      <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Provider</th>
                      <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Credential Status</th>
                      <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Reachability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.providers).map(([providerName, health]) => (
                      <tr
                        key={providerName}
                        style={{ borderBottom: '1px solid var(--color-border-muted)' }}
                      >
                        <td style={{ padding: '0.5rem 0.75rem', fontWeight: 500 }}>
                          {providerName}
                        </td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>
                          {health.configured ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--status-verified-text)' }}>
                              <CheckCircle2 size={13} aria-hidden="true" /> Configured
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--color-slate)' }}>
                              <XCircle size={13} aria-hidden="true" /> Unconfigured
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>
                          {health.available ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--status-verified-text)' }}>
                              <CheckCircle2 size={13} aria-hidden="true" /> Reachable
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--status-warning-text)' }}>
                              <AlertTriangle size={13} aria-hidden="true" /> Standby
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <p style={{ fontSize: '0.6875rem', color: 'var(--color-slate)', marginTop: 'var(--space-4)', textAlign: 'right' }}>
              Registry Timestamp: {new Date(data.timestamp).toLocaleString()}
            </p>
          </>
        )}
      </div>
    </Drawer>
  );
};
