import React, { useState } from 'react';
import { Scale, CheckCircle2, Lock, Edit3 } from 'lucide-react';
import { Badge, Button } from '../common';
import type { ValidationIssue } from '../../types/domain';
import './ai.css';

export interface DiscrepancyAdjudicationProps {
  issues: ValidationIssue[];
  onToggleResolve?: (issueId: string) => void;
  onOpenModelRegistry?: () => void;
  onClarifyCell?: (tableId: string, rowIdx: number | null, colIdx: number | null) => void;
}

export const DiscrepancyAdjudication: React.FC<DiscrepancyAdjudicationProps> = ({
  issues,
  onToggleResolve,
  onOpenModelRegistry,
  onClarifyCell,
}) => {
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());
  const [showResolved, setShowResolved] = useState<boolean>(true);

  if (!issues || issues.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-6)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--color-verified-bg)',
          border: '1px solid var(--color-verified-border)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          color: 'var(--color-verified-text)',
        }}
        data-testid="no-discrepancies-banner"
      >
        <CheckCircle2 size={18} aria-hidden="true" />
        <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
          Zero arithmetic or structural discrepancies detected. All checked sums are internally consistent.
        </span>
      </div>
    );
  }

  const handleToggle = (id: string) => {
    setResolvedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    onToggleResolve?.(id);
  };

  const displayedIssues = showResolved
    ? issues
    : issues.filter((iss) => !resolvedIds.has(iss.issue_id) && !iss.resolved);

  return (
    <div className="ds-ai-section" data-testid="discrepancy-adjudication-section">
      {/* 1. Truthful AI Model Advisory Notice */}
      <div className="ds-ai-callout">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="ds-ai-callout-title">
            <Lock size={12} aria-hidden="true" /> Multi-LLM Advisory Status: Standby / Unverified
          </span>
          {onOpenModelRegistry && (
            <button
              type="button"
              className="ds-btn ds-btn-ghost ds-btn-sm"
              style={{ fontSize: '11px', padding: '2px 8px', height: 'auto' }}
              onClick={onOpenModelRegistry}
            >
              View Model Registry
            </button>
          )}
        </div>
        <p className="ds-ai-callout-text">
          All 7 candidate models currently remain disabled, unverified, and non-operational on the backend.
          Discrepancies below are detected by the authoritative deterministic Decimal arithmetic engine.
          No LLM predictions or automated auto-balancing have modified these records.
        </p>
      </div>

      {/* 2. Discrepancy Header & Filter */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Scale size={16} style={{ color: 'var(--color-discrepancy-text)' }} aria-hidden="true" />
          <h3 style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
            Detected Discrepancies ({issues.length})
          </h3>
        </div>
        <label
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-slate)',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
          />
          Show acknowledged findings
        </label>
      </div>

      {/* 3. Discrepancy Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {displayedIssues.map((issue) => {
          const isAcknowledged = resolvedIds.has(issue.issue_id) || issue.resolved;

          return (
            <div
              key={issue.issue_id}
              className="ds-discrepancy-card"
              style={{
                opacity: isAcknowledged ? 0.7 : 1.0,
                backgroundColor: isAcknowledged ? 'var(--color-warm-paper)' : 'var(--color-pure-white)',
              }}
              data-testid={`discrepancy-card-${issue.issue_id}`}
            >
              <div className="ds-discrepancy-meta">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <Badge variant={isAcknowledged ? 'neutral' : 'discrepancy'} size="sm">
                    {issue.issue_code}
                  </Badge>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
                    Table: {issue.table_id}
                    {issue.row_idx !== null ? ` • Row ${issue.row_idx + 1}` : ''}
                    {issue.col_idx !== null ? ` • Col ${issue.col_idx + 1}` : ''}
                    {' '}(Page {issue.source_page})
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {onClarifyCell && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onClarifyCell(issue.table_id, issue.row_idx, issue.col_idx)}
                      icon={<Edit3 size={12} aria-hidden="true" />}
                    >
                      Clarify & Edit Source Cell
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggle(issue.issue_id)}
                  >
                    {isAcknowledged ? 'Re-open Finding' : 'Acknowledge Discrepancy'}
                  </Button>
                </div>
              </div>

              <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-ink)' }}>
                {issue.description}
              </p>

              {(issue.expected_value || issue.actual_value) && (
                <div className="ds-discrepancy-math">
                  {issue.actual_value !== null && (
                    <span>
                      Printed in Source: <strong>{issue.actual_value}</strong>
                    </span>
                  )}
                  {issue.expected_value !== null && (
                    <>
                      <span>•</span>
                      <span>
                        Calculated Sum: <strong>{issue.expected_value}</strong>
                      </span>
                    </>
                  )}
                </div>
              )}

              {/* Deterministic Explanation Policy */}
              <div
                style={{
                  fontSize: '11px',
                  color: 'var(--color-slate)',
                  fontStyle: 'italic',
                  paddingTop: 2,
                }}
              >
                Policy: Raw printed totals are preserved without alteration. Auto-balancing is prohibited (DECISION-007).
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
