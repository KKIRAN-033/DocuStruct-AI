import React, { useState } from 'react';
import { Table, Plus, Edit2, Trash2 } from 'lucide-react';
import { Badge, Button, Modal } from '../common';
import type { CanonicalTable, CellRecord, DataType } from '../../types/domain';
import './table.css';

export interface TableGridProps {
  tables: CanonicalTable[];
  selectedCell?: CellRecord | null;
  onSelectCell?: (cell: CellRecord) => void;
  activeTableIdx?: number;
  onSelectTable?: (idx: number) => void;
  onAddRow?: (tableId: string, values: string[]) => void;
  onDeleteRow?: (tableId: string, rowIdx: number) => void;
  onEditRow?: (tableId: string, rowIdx: number, values: string[]) => void;
  onUpdateCell?: (tableId: string, rowIdx: number, colIdx: number, newValue: string) => void;
}

export const TableGrid: React.FC<TableGridProps> = ({
  tables,
  selectedCell,
  onSelectCell,
  activeTableIdx: controlledActiveTableIdx,
  onSelectTable,
  onAddRow,
  onDeleteRow,
  onEditRow,
  onUpdateCell,
}) => {
  const [internalActiveIdx, setInternalActiveIdx] = useState<number>(0);
  const activeTableIdx = controlledActiveTableIdx !== undefined ? controlledActiveTableIdx : internalActiveIdx;

  const [rowModal, setRowModal] = useState<{
    isOpen: boolean;
    mode: 'add' | 'edit';
    rowIdx?: number;
    values: string[];
  }>({
    isOpen: false,
    mode: 'add',
    values: [],
  });

  const [editingCell, setEditingCell] = useState<{
    rowIdx: number;
    colIdx: number;
  } | null>(null);

  const [inlineValue, setInlineValue] = useState<string>('');

  if (!tables || tables.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-8)',
          textAlign: 'center',
          backgroundColor: 'var(--color-warm-paper)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-muted)',
          color: 'var(--color-slate)',
        }}
      >
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)' }}>
          No canonical tables extracted in this report.
        </p>
      </div>
    );
  }

  const currentTable = tables[activeTableIdx] || tables[0];
  const headers =
    currentTable.normalized_headers && currentTable.normalized_headers.length > 0
      ? currentTable.normalized_headers
      : currentTable.original_headers;

  const isNumericType = (type?: DataType): boolean => {
    return (
      type === 'DECIMAL' ||
      type === 'INTEGER' ||
      type === 'HIGH_PRECISION_DECIMAL'
    );
  };

  const isSummaryRow = (row: CellRecord[]): boolean => {
    const summaryRegex = /^(total|subtotal|grand total|sum|balance|net total)/i;
    for (const cell of row) {
      const val = (cell.accepted_value || cell.raw_value).trim();
      if (val && summaryRegex.test(val)) {
        return true;
      }
    }
    return false;
  };

  const isRepeatedHeaderRow = (row: CellRecord[]): boolean => {
    if (row.length !== headers.length) return false;
    let matchCount = 0;
    let hasNumeric = false;
    for (let c = 0; c < row.length; c++) {
      if (row[c].numeric_decimal !== null) {
        hasNumeric = true;
      }
      const val = (row[c].accepted_value || row[c].raw_value || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
      const hdr = (headers[c] || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
      if (val && hdr && (val === hdr || val.includes(hdr) || hdr.includes(val))) {
        matchCount++;
      }
    }
    return !hasNumeric && matchCount >= headers.length - 1;
  };

  return (
    <div className="ds-table-section" data-testid="table-grid-section">
      {/* 1. Canonical Table Tabs (if multiple tables) */}
      {tables.length > 1 && (
        <div className="ds-table-tabs" role="tablist" aria-label="Extracted Canonical Tables">
          {tables.map((t, idx) => {
            const isActive = idx === activeTableIdx;
            const pagesLabel =
              t.source_pages.length > 1
                ? `Pages ${t.source_pages[0]}-${t.source_pages[t.source_pages.length - 1]}`
                : `Page ${t.source_pages[0] || 1}`;

            return (
              <button
                key={t.table_id || idx}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={`ds-table-tab ${isActive ? 'ds-table-tab-active' : ''}`}
                onClick={() => {
                  setInternalActiveIdx(idx);
                  onSelectTable?.(idx);
                }}
              >
                <Table size={14} aria-hidden="true" />
                <span>
                  Table {idx + 1}: {pagesLabel}
                </span>
                <Badge variant={t.structural_checks_passed ? 'neutral' : 'warning'} size="sm">
                  {t.rows.length} rows × {headers.length} cols
                </Badge>
              </button>
            );
          })}
        </div>
      )}

      {/* 2. Table Toolbar & Context */}
      <div className="ds-table-toolbar">
        <div className="ds-table-meta">
          <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
            {currentTable.title || `Canonical Table (${currentTable.table_id})`}
          </span>
          <span>•</span>
          <span>
            {currentTable.rows.length} Rows × {headers.length} Columns
          </span>
          <span>•</span>
          <span>
            Pages: {currentTable.source_pages.join(', ')}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Button
            variant="primary"
            size="sm"
            data-testid="add-row-button"
            onClick={() => {
              setRowModal({
                isOpen: true,
                mode: 'add',
                values: new Array(headers.length).fill(''),
              });
            }}
          >
            <Plus size={14} style={{ marginRight: '4px' }} />
            Add Row
          </Button>
          <Badge
            variant={currentTable.structural_checks_passed ? 'verified' : 'warning'}
            size="sm"
          >
            Structure: {currentTable.structural_checks_passed ? 'Valid' : 'Anomaly'}
          </Badge>
          <Badge
            variant={
              currentTable.math_validation_outcome === 'PASSED'
                ? 'verified'
                : currentTable.math_validation_outcome === 'PASSED_WITH_WARNINGS'
                ? 'warning'
                : currentTable.math_validation_outcome === 'FAILED_VALIDATION'
                ? 'discrepancy'
                : 'neutral'
            }
            size="sm"
          >
            Arithmetic: {currentTable.math_validation_outcome}
          </Badge>
        </div>
      </div>

      {/* 3. Interactive Data Grid Container */}
      <div className="ds-table-container">
        <table className="ds-grid-table" role="grid" aria-label="Extracted Table Grid">
          <thead>
            <tr>
              {headers.map((hdr, colIdx) => {
                const colType = currentTable.column_types?.[colIdx] || 'STRING';
                const isNumeric = isNumericType(colType);

                return (
                  <th
                    key={colIdx}
                    scope="col"
                    style={{ textAlign: isNumeric ? 'right' : 'left' }}
                  >
                    <div className="ds-th-content">
                      <span className="ds-th-title" title={hdr || `Column ${colIdx + 1}`}>
                        {hdr || `[Col ${colIdx + 1}]`}
                      </span>
                      <span className="ds-th-type">{colType}</span>
                    </div>
                  </th>
                );
              })}
              <th scope="col" style={{ width: '64px', textAlign: 'center' }}>
                <div className="ds-th-content" style={{ alignItems: 'center' }}>
                  <span className="ds-th-title">Actions</span>
                  <span className="ds-th-type">EDIT</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {currentTable.rows
              .map((row, actualRowIdx) => ({ row, actualRowIdx }))
              .filter(({ row }) => !isRepeatedHeaderRow(row))
              .map(({ row, actualRowIdx }) => {
                const summary = isSummaryRow(row);

                return (
                  <tr
                    key={actualRowIdx}
                    className={summary ? 'ds-row-summary' : undefined}
                    data-testid={`table-row-${actualRowIdx}`}
                  >
                    {row.map((cell, colIdx) => {
                      const colType = currentTable.column_types?.[colIdx] || cell.data_type;
                      const isNumeric = isNumericType(colType);
                      const isSelected =
                        selectedCell !== null &&
                        selectedCell?.table_id === cell.table_id &&
                        selectedCell?.row_idx === cell.row_idx &&
                        selectedCell?.col_idx === cell.col_idx;
                      const isCellEditing =
                        editingCell !== null &&
                        editingCell.rowIdx === actualRowIdx &&
                        editingCell.colIdx === colIdx;

                      return (
                        <td
                          key={colIdx}
                          tabIndex={0}
                          role="gridcell"
                          aria-selected={isSelected}
                          className={`
                            ${isNumeric ? 'ds-cell-numeric' : ''}
                            ${isSelected ? 'ds-cell-selected' : ''}
                          `}
                          onClick={() => onSelectCell?.(cell)}
                          onDoubleClick={() => {
                            setEditingCell({ rowIdx: actualRowIdx, colIdx });
                            setInlineValue(cell.accepted_value || cell.raw_value || '');
                          }}
                          onKeyDown={(e) => {
                            if (!isCellEditing && (e.key === 'Enter' || e.key === ' ')) {
                              e.preventDefault();
                              onSelectCell?.(cell);
                            }
                          }}
                          title={`Row ${actualRowIdx + 1}, Col ${colIdx + 1}: ${cell.accepted_value} (Double-click to edit)`}
                        >
                          {isCellEditing ? (
                            <input
                              autoFocus
                              type="text"
                              className="ds-cell-inline-input"
                              data-testid={`inline-edit-input-${actualRowIdx}-${colIdx}`}
                              value={inlineValue}
                              onChange={(e) => setInlineValue(e.target.value)}
                              onBlur={() => {
                                if (inlineValue !== cell.accepted_value) {
                                  onUpdateCell?.(currentTable.table_id, actualRowIdx, colIdx, inlineValue);
                                }
                                setEditingCell(null);
                              }}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  if (inlineValue !== cell.accepted_value) {
                                    onUpdateCell?.(currentTable.table_id, actualRowIdx, colIdx, inlineValue);
                                  }
                                  setEditingCell(null);
                                } else if (e.key === 'Escape') {
                                  e.preventDefault();
                                  setEditingCell(null);
                                }
                              }}
                              onClick={(e) => e.stopPropagation()}
                            />
                          ) : (
                            <div
                              className={`ds-cell-content ${
                                isNumeric ? 'ds-cell-content-numeric' : ''
                              }`}
                            >
                              {/* Formula Risk Indicator without modifying text */}
                              {cell.formula_risk_detected && (
                                <span
                                  className="ds-fx-badge"
                                  title="Formula-risk character detected (=, +, -, @, \t, \r). Cell text preserved without mutation."
                                >
                                  fx
                                </span>
                              )}

                              {/* Candidate Indicator */}
                              {cell.inferred_candidate_value && (
                                <span
                                  className="ds-candidate-dot"
                                  title={`Candidate proposal available: ${cell.inferred_candidate_value}`}
                                />
                              )}

                              {/* Cell Value */}
                              <span>{cell.accepted_value}</span>
                            </div>
                          )}
                        </td>
                      );
                    })}

                    {/* Row action controls (placed at right edge) */}
                    <td
                      style={{ width: '64px', textAlign: 'center', whiteSpace: 'nowrap' }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <button
                          type="button"
                          className="ds-btn-row-action"
                          title={`Edit Row #${actualRowIdx + 1}`}
                          aria-label={`Edit row ${actualRowIdx + 1}`}
                          data-testid={`edit-row-${actualRowIdx}`}
                          onClick={() => {
                            setRowModal({
                              isOpen: true,
                              mode: 'edit',
                              rowIdx: actualRowIdx,
                              values: headers.map((_, cIdx) => row[cIdx]?.accepted_value ?? ''),
                            });
                          }}
                        >
                          <Edit2 size={13} aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          className="ds-btn-row-action ds-btn-row-delete"
                          title={`Delete Row #${actualRowIdx + 1}`}
                          aria-label={`Delete row ${actualRowIdx + 1}`}
                          data-testid={`delete-row-${actualRowIdx}`}
                          onClick={() => {
                            const isConfirmed =
                              typeof window === 'undefined' ||
                              typeof window.confirm !== 'function' ||
                              window.confirm(`Delete row #${actualRowIdx + 1}?`);
                            if (isConfirmed) {
                              onDeleteRow?.(currentTable.table_id, actualRowIdx);
                            }
                          }}
                        >
                          <Trash2 size={13} aria-hidden="true" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* 4. Table Bottom Footer Quick-Action */}
      <div className="ds-table-footer-actions">
        <Button
          variant="secondary"
          size="sm"
          data-testid="add-row-bottom-button"
          onClick={() => {
            setRowModal({
              isOpen: true,
              mode: 'add',
              values: new Array(headers.length).fill(''),
            });
          }}
        >
          <Plus size={14} style={{ marginRight: '6px' }} />
          Add Row to Table
        </Button>
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
          ⚡ <strong>Autonomous Editor:</strong> Click <em>+ Add Row</em> to insert records or double-click any cell to edit in-place. All updates automatically export to Excel.
        </span>
      </div>

      {/* 5. Add / Edit Row Modal */}
      {rowModal.isOpen && (
        <Modal
          isOpen={rowModal.isOpen}
          onClose={() => setRowModal({ isOpen: false, mode: 'add', values: [] })}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>{rowModal.mode === 'add' ? 'Add New Row' : `Edit Row #${(rowModal.rowIdx ?? 0) + 1}`}</span>
              <Badge variant="neutral" size="sm">
                {currentTable.title || `Table ${activeTableIdx + 1}`}
              </Badge>
            </div>
          }
          maxWidth="38rem"
          footer={
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)', width: '100%' }}>
              <Button
                variant="secondary"
                size="sm"
                type="button"
                onClick={() => setRowModal({ isOpen: false, mode: 'add', values: [] })}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="button"
                data-testid="submit-row-modal"
                onClick={() => {
                  if (rowModal.mode === 'add') {
                    onAddRow?.(currentTable.table_id, rowModal.values);
                  } else if (rowModal.rowIdx !== undefined) {
                    onEditRow?.(currentTable.table_id, rowModal.rowIdx, rowModal.values);
                  }
                  setRowModal({ isOpen: false, mode: 'add', values: [] });
                }}
              >
                {rowModal.mode === 'add' ? 'Add Row' : 'Save Changes'}
              </Button>
            </div>
          }
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-3)', maxHeight: '60vh', overflowY: 'auto', padding: 'var(--space-1)' }}>
            {headers.map((hdr, cIdx) => {
              const colType = currentTable.column_types?.[cIdx] || 'STRING';
              return (
                <div key={cIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-ink)', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{hdr || `Column ${cIdx + 1}`}</span>
                    <span style={{ fontSize: '10px', color: 'var(--color-slate-light)', fontFamily: 'var(--font-family-mono)' }}>{colType}</span>
                  </label>
                  <input
                    type="text"
                    value={rowModal.values[cIdx] || ''}
                    onChange={(e) => {
                      const next = [...rowModal.values];
                      next[cIdx] = e.target.value;
                      setRowModal((prev) => ({ ...prev, values: next }));
                    }}
                    placeholder={`Enter ${hdr || `Column ${cIdx + 1}`}`}
                    className="ds-modal-input"
                    data-testid={`row-modal-input-${cIdx}`}
                  />
                </div>
              );
            })}
          </div>
        </Modal>
      )}
    </div>
  );
};

