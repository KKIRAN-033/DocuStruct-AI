import React from 'react';
import { GitMerge } from 'lucide-react';
import { Badge } from '../common';
import type { StitchAuditEvent } from '../../types/domain';
import './audit.css';

export interface StitchAuditProps {
  stitchEvents: StitchAuditEvent[];
}

export const StitchAudit: React.FC<StitchAuditProps> = ({ stitchEvents }) => {
  if (!stitchEvents || stitchEvents.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-4)',
          color: 'var(--color-slate)',
          fontSize: 'var(--font-size-sm)',
          backgroundColor: 'var(--color-warm-paper)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--color-border-muted)',
        }}
        data-testid="no-stitch-events"
      >
        No cross-page table stitch events recorded for this document. Tables are single-page or independent.
      </div>
    );
  }

  return (
    <div className="ds-audit-section" data-testid="stitch-audit-section">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <GitMerge size={16} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
        <h3 style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
          Multipage Stitch Audit Trail ({stitchEvents.length} Events)
        </h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {stitchEvents.map((event, idx) => {
          const isConfirmed = event.decision === 'STITCH_CONFIRMED';
          const isRejected = event.decision === 'STITCH_REJECTED';

          return (
            <div key={idx} className="ds-stitch-card" data-testid={`stitch-card-${idx}`}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-ink)' }}>
                  Pages {event.upper_page} → {event.lower_page}
                </span>
                <Badge
                  variant={isConfirmed ? 'verified' : isRejected ? 'discrepancy' : 'warning'}
                >
                  {event.decision}
                </Badge>
              </div>

              {/* 7 Decision Factors Breakdown */}
              <div className="ds-stitch-factors-grid">
                <div className="ds-stitch-factor-item">
                  <span className="ds-factor-label">Header Similarity</span>
                  <span className="ds-factor-value">
                    {(event.header_similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="ds-stitch-factor-item">
                  <span className="ds-factor-label">Column Overlap</span>
                  <span className="ds-factor-value">
                    {(event.col_overlap_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="ds-stitch-factor-item">
                  <span className="ds-factor-label">Type Compatibility</span>
                  <span className="ds-factor-value">
                    {(event.type_compatibility_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="ds-stitch-factor-item">
                  <span className="ds-factor-label">Headers Stripped</span>
                  <span className="ds-factor-value">
                    {event.repeated_header_rows_stripped} rows
                  </span>
                </div>
              </div>

              {/* Rationale and reasons */}
              {event.reasons && event.reasons.length > 0 && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
                  <span style={{ fontWeight: 600 }}>Evaluation Rationale: </span>
                  {event.reasons.join('; ')}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
