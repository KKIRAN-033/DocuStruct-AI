import React from 'react';
import { Drawer, Badge, Button } from '../common';
import { Sparkles, ShieldAlert, Check, X, Lock } from 'lucide-react';
import type { CellRecord, CanonicalTable } from '../../types/domain';
import './ai.css';

export interface CandidateProposalDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  cell: CellRecord | null;
  table: CanonicalTable | null;
  onAcceptProposal?: (cell: CellRecord, proposedValue: string) => void;
  onRejectProposal?: (cell: CellRecord) => void;
}

export const CandidateProposalDrawer: React.FC<CandidateProposalDrawerProps> = ({
  isOpen,
  onClose,
  cell,
  table,
  onAcceptProposal,
  onRejectProposal,
}) => {
  if (!cell || !isOpen) return null;

  // Locate corresponding CorrectionRecord if present
  const correctionRecord = table?.correction_records?.find(
    (c) =>
      c.table_id === cell.table_id &&
      c.row_idx === cell.row_idx &&
      c.col_idx === cell.col_idx
  );

  const proposedValue =
    cell.inferred_candidate_value ||
    correctionRecord?.proposed_value ||
    cell.accepted_value;

  const evidenceSource =
    correctionRecord?.evidence_source || 'VECTOR_GRID_GEOMETRY';

  const evidenceSummary =
    correctionRecord?.evidence_summary ||
    'Corroborated by digital cell boundaries and character alignment streams.';

  // Check for auto-balancing prohibition
  // 1. Is this a summary row (Total, Subtotal, Grand Total)?
  const isTotalRow = Boolean(
    table?.rows[cell.row_idx]?.some((c) =>
      /^(total|subtotal|grand total|sum|balance)/i.test((c.accepted_value || c.raw_value).trim())
    )
  );

  // 2. Is this explicitly marked as an auto-balance rejection in the backend record?
  const isAutoBalanceBlocked =
    isTotalRow ||
    correctionRecord?.decision === 'REJECTED_AUTO_BALANCE_PRESERVED_RAW' ||
    correctionRecord?.inferred_candidate_only === true;

  const handleAccept = () => {
    if (isAutoBalanceBlocked) return;
    onAcceptProposal?.(cell, proposedValue);
    onClose();
  };

  const handleReject = () => {
    onRejectProposal?.(cell);
    onClose();
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Sparkles size={16} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
          <span>Candidate Proposal Review</span>
          <Badge variant="neutral" size="sm">
            R{cell.row_idx + 1} : C{cell.col_idx + 1}
          </Badge>
        </div>
      }
      width="34rem"
    >
      <div className="ds-ai-section" data-testid="candidate-proposal-drawer">
        {/* Model Authority Disclaimer */}
        <div className="ds-ai-callout">
          <span className="ds-ai-callout-title">
            <Lock size={12} aria-hidden="true" /> Evidence-Gated Human Review
          </span>
          <p className="ds-ai-callout-text">
            All AI candidate proposals require verifiable source evidence and human editorial confirmation. Inferred values never mutate raw source text.
          </p>
        </div>

        {/* Auto-balancing prohibition warning */}
        {isAutoBalanceBlocked && (
          <div className="ds-auto-balance-warning" role="alert" data-testid="autobalance-prohibition-warning">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={16} aria-hidden="true" />
              <strong style={{ fontSize: 'var(--font-size-xs)' }}>
                Auto-Balancing Prohibited (DECISION-007 & DECISION-011)
              </strong>
            </div>
            <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', lineHeight: 'var(--line-height-normal)' }}>
              This cell resides in a total or summary row. The pipeline strictly prohibits auto-balancing totals or altering printed arithmetic outcomes to force consistency. The raw source total is preserved; inferred candidates are recorded for review only.
            </p>
          </div>
        )}

        {/* Values Comparison Grid */}
        <div className="ds-proposal-card">
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-slate)' }}>
            Cell Value Comparison
          </span>
          <div className="ds-proposal-values-grid">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: '11px', color: 'var(--color-slate)', textTransform: 'uppercase' }}>
                Immutable Raw Source
              </span>
              <div className="ds-proposal-val-box ds-val-raw" data-testid="proposal-raw-value">
                {cell.raw_value.length > 0 ? cell.raw_value : <em style={{ color: 'var(--color-slate-light)' }}>[empty]</em>}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: '11px', color: 'var(--color-slate)', textTransform: 'uppercase' }}>
                Proposed Candidate
              </span>
              <div className="ds-proposal-val-box ds-val-proposed" data-testid="proposal-candidate-value">
                {proposedValue}
              </div>
            </div>
          </div>
        </div>

        {/* Traceable Evidence Metadata */}
        <div className="ds-proposal-card">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-slate)' }}>
              Traceable Evidence Provenance
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
                Evidence Source:
              </span>
              <Badge variant="verified" size="sm">
                {evidenceSource}
              </Badge>
            </div>
            <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', lineHeight: 'var(--line-height-normal)' }}>
              {evidenceSummary}
            </p>
          </div>
        </div>

        {/* Human Editorial Decision Actions */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: 'var(--space-3)',
            marginTop: 'var(--space-4)',
            paddingTop: 'var(--space-4)',
            borderTop: '1px solid var(--color-border-muted)',
          }}
        >
          <Button variant="ghost" size="sm" onClick={handleReject}>
            <X size={14} style={{ marginRight: 6 }} aria-hidden="true" />
            Reject / Dismiss Proposal
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleAccept}
            disabled={isAutoBalanceBlocked}
            data-testid="accept-proposal-btn"
          >
            <Check size={14} style={{ marginRight: 6 }} aria-hidden="true" />
            {isAutoBalanceBlocked ? 'Accept Blocked (Total Row)' : 'Accept as Accepted Value'}
          </Button>
        </div>
      </div>
    </Drawer>
  );
};
