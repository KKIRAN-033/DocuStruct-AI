import React, { useState, useEffect } from 'react';
import { Drawer, Badge, Button } from '../common';
import { Lock, Sparkles, Edit3, Check, HelpCircle } from 'lucide-react';
import type { CellRecord } from '../../types/domain';
import './table.css';

export interface CellInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  cell: CellRecord | null;
  onOpenCandidateProposal?: (cell: CellRecord) => void;
  onUpdateCellValue?: (cell: CellRecord, newValue: string) => void;
}

export const CellInspector: React.FC<CellInspectorProps> = ({
  isOpen,
  onClose,
  cell,
  onOpenCandidateProposal,
  onUpdateCellValue,
}) => {
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editValue, setEditValue] = useState<string>('');

  useEffect(() => {
    if (cell) {
      setEditValue(cell.accepted_value || cell.raw_value);
      setIsEditing(false);
    }
  }, [cell]);

  if (!cell) return null;

  const hasBbox = cell.bbox !== null;

  const handleSave = () => {
    if (onUpdateCellValue && editValue.trim() !== '') {
      onUpdateCellValue(cell, editValue.trim());
    }
    setIsEditing(false);
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span>Cell Provenance & Inspection</span>
          <Badge variant="neutral" size="sm">
            R{cell.row_idx + 1} : C{cell.col_idx + 1}
          </Badge>
        </div>
      }
      width="34rem"
    >
      <div className="ds-inspector-section" data-testid="cell-inspector-panel">
        {/* Cell Location Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingBottom: 'var(--space-3)',
            borderBottom: '1px solid var(--color-border-muted)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
              Target Table & Page
            </span>
            <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
              Table: {cell.table_id} (Page {cell.source_page})
            </span>
          </div>
          <Badge
            variant={
              cell.quality_status === 'CORRECTED_WITH_EVIDENCE'
                ? 'verified'
                : cell.quality_status === 'ILLEGIBLE_OR_MISSING' ||
                  cell.quality_status === 'ANOMALY_FLAGGED'
                ? 'warning'
                : 'neutral'
            }
          >
            {cell.quality_status}
          </Badge>
        </div>

        {/* 1. Immutable Raw Value */}
        <div className="ds-inspector-field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <label className="ds-field-label">Immutable Raw Value</label>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: '11px',
                color: 'var(--color-slate)',
              }}
            >
              <Lock size={12} aria-hidden="true" /> Unalterable Source Evidence
            </span>
          </div>
          <div className="ds-field-value ds-field-raw ds-field-value-mono" data-testid="cell-raw-value">
            {cell.raw_value.length > 0 ? cell.raw_value : <em style={{ color: 'var(--color-slate-light)' }}>[empty string]</em>}
          </div>
        </div>

        {/* 2. Accepted Value with User Clarification & Edit */}
        <div className="ds-inspector-field">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <label className="ds-field-label" style={{ margin: 0 }}>Accepted Value (Operational)</label>
            {!isEditing && onUpdateCellValue && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(true)}
                icon={<Edit3 size={12} aria-hidden="true" />}
              >
                Clarify / Edit
              </Button>
            )}
          </div>

          {isEditing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <input
                type="text"
                className="ds-input ds-field-value-mono"
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-cobalt)',
                  fontSize: 'var(--font-size-sm)',
                }}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                autoFocus
                placeholder="Enter clarified value..."
              />
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSave}
                  icon={<Check size={13} aria-hidden="true" />}
                >
                  Save & Re-verify
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setEditValue(cell.accepted_value || cell.raw_value);
                    setIsEditing(false);
                  }}
                >
                  Cancel
                </Button>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--color-slate)' }}>
                Human clarification updates operational table extraction & export while strictly preserving immutable raw source character evidence.
              </span>
            </div>
          ) : (
            <div className="ds-field-value ds-field-value-mono" data-testid="cell-accepted-value">
              {cell.accepted_value.length > 0 ? cell.accepted_value : <em style={{ color: 'var(--color-slate-light)' }}>[empty string]</em>}
            </div>
          )}
        </div>

        {/* Deterministic Extraction Evidence & Ambiguity Diagnosis */}
        <div
          style={{
            padding: 'var(--space-3)',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--color-warm-paper)',
            border: '1px solid var(--color-border-muted)',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <HelpCircle size={14} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-ink)' }}>
              Deterministic Extraction Evidence & Audit Trail
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-slate)', lineHeight: 1.4 }}>
            Original token &quot;<code>{cell.raw_value}</code>&quot; captured on Page {cell.source_page} at coordinates (x0: {cell.bbox?.x0.toFixed(1) ?? '—'}, y0: {cell.bbox?.y0.toFixed(1) ?? '—'}). If character ambiguity or OCR confusion occurred, edit the Accepted Value above to clarify for downstream table recalculation.
          </p>
        </div>

        {/* 3. Normalized & Decimal Representation */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
          <div className="ds-inspector-field">
            <label className="ds-field-label">Normalized Value</label>
            <div className="ds-field-value ds-field-value-mono">
              {cell.normalized_value ?? '—'}
            </div>
          </div>
          <div className="ds-inspector-field">
            <label className="ds-field-label">Exact Decimal</label>
            <div className="ds-field-value ds-field-value-mono">
              {cell.numeric_decimal ?? '—'}
            </div>
          </div>
        </div>

        {/* 4. Type & Formula Risk */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
          <div className="ds-inspector-field">
            <label className="ds-field-label">Inferred Data Type</label>
            <div className="ds-field-value">
              <Badge variant="neutral" size="sm">
                {cell.data_type}
              </Badge>
            </div>
          </div>
          <div className="ds-inspector-field">
            <label className="ds-field-label">Formula Risk Status</label>
            <div className="ds-field-value">
              {cell.formula_risk_detected ? (
                <Badge variant="warning" size="sm">
                  Formula Risk (fx)
                </Badge>
              ) : (
                <Badge variant="verified" size="sm">
                  Safe (No Prefix)
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* 5. Inferred Candidate Value (if present) */}
        {cell.inferred_candidate_value && (
          <div
            style={{
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--color-cobalt-light)',
              border: '1px solid #BFDBFE',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={14} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-cobalt)' }}>
                  Inferred Candidate Proposal Available
                </span>
              </div>
              <Badge variant="deferred" size="sm">Candidate</Badge>
            </div>
            <div className="ds-field-value ds-field-value-mono" style={{ backgroundColor: '#fff' }}>
              {cell.inferred_candidate_value}
            </div>
            {onOpenCandidateProposal && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onOpenCandidateProposal(cell)}
              >
                Review Evidence & Proposal
              </Button>
            )}
          </div>
        )}

        {/* 6. Bounding Box Geometry */}
        <div className="ds-inspector-field">
          <label className="ds-field-label">Source Coordinates (PDF Bounding Box)</label>
          {hasBbox ? (
            <div className="ds-bbox-grid">
              <div className="ds-bbox-item">
                <span>x0:</span> <span>{cell.bbox?.x0.toFixed(2)} pt</span>
              </div>
              <div className="ds-bbox-item">
                <span>y0:</span> <span>{cell.bbox?.y0.toFixed(2)} pt</span>
              </div>
              <div className="ds-bbox-item">
                <span>x1:</span> <span>{cell.bbox?.x1.toFixed(2)} pt</span>
              </div>
              <div className="ds-bbox-item">
                <span>y1:</span> <span>{cell.bbox?.y1.toFixed(2)} pt</span>
              </div>
            </div>
          ) : (
            <div className="ds-field-value" style={{ color: 'var(--color-slate)' }}>
              No bounding box available (synthetic or unpositioned cell)
            </div>
          )}
        </div>

        {/* 7. Extraction Method & Notes */}
        <div className="ds-inspector-field">
          <label className="ds-field-label">Extraction Method</label>
          <div className="ds-field-value ds-field-value-mono">
            {cell.extraction_method || 'DIGITAL_LINE_GEOMETRY'}
          </div>
        </div>

        {cell.notes && cell.notes.length > 0 && (
          <div className="ds-inspector-field">
            <label className="ds-field-label">Cell Audit Notes</label>
            <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
              {cell.notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Drawer>
  );
};
