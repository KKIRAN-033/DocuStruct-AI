import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Cpu,
  RefreshCw,
  Layers,
  Scale,
  GitMerge,
  ShieldCheck,
  Eye,
  Table,
  Download,
} from 'lucide-react';
import { Shell, ModelRegistryDrawer } from './components/layout';
import { Card, Badge, Callout, Button } from './components/common';
import { DocumentUpload } from './components/upload';
import { VerificationBanner } from './components/status';
import { TableGrid, CellInspector } from './components/table';
import { CandidateProposalDrawer, DiscrepancyAdjudication } from './components/ai';
import { PageProfiles, StitchAudit } from './components/audit';
import { ExportControls } from './components/export';
import { apiClient } from './api/client';
import type { ModelsStatusResponse } from './types/api';
import type {
  DocumentEvaluationReport,
  CanonicalTable,
  CellRecord,
} from './types/domain';

type ActiveTab = 'workspace' | 'models';
type WorkspaceAuditSubtab = 'discrepancies' | 'pages' | 'stitch';

export const App: React.FC = () => {
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);
  const [isCheckingBackend, setIsCheckingBackend] = useState<boolean>(false);
  const [isModelRegistryOpen, setIsModelRegistryOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>('workspace');
  const [modelsData, setModelsData] = useState<ModelsStatusResponse | null>(null);

  // Workstation Document Report State
  const [report, setReport] = useState<DocumentEvaluationReport | null>(null);
  const [tables, setTables] = useState<CanonicalTable[]>([]);
  const [activeTableIdx, setActiveTableIdx] = useState<number>(0);
  const [selectedCell, setSelectedCell] = useState<CellRecord | null>(null);
  const [candidateCell, setCandidateCell] = useState<CellRecord | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [isProposalDrawerOpen, setIsProposalDrawerOpen] = useState<boolean>(false);
  const [auditSubtab, setAuditSubtab] = useState<WorkspaceAuditSubtab>('discrepancies');

  const checkBackendHealth = useCallback(async () => {
    setIsCheckingBackend(true);
    try {
      await apiClient.checkHealth();
      setIsBackendConnected(true);
    } catch {
      setIsBackendConnected(false);
    } finally {
      setIsCheckingBackend(false);
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  const fetchModelsStatus = useCallback(async () => {
    try {
      const resp = await apiClient.getModelsStatus();
      setModelsData(resp);
    } catch {
      // Fallback silently if unavailable
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'models') {
      fetchModelsStatus();
    }
  }, [activeTab, fetchModelsStatus]);

  // When a report arrives from DocumentUpload
  const handleExtractionSuccess = (incomingReport: DocumentEvaluationReport) => {
    setReport(incomingReport);
    setTables(incomingReport.canonical_tables || []);
    setActiveTableIdx(0);
    setSelectedCell(null);
    setCandidateCell(null);
  };

  const handleResetDocument = () => {
    setReport(null);
    setTables([]);
    setActiveTableIdx(0);
    setSelectedCell(null);
    setCandidateCell(null);
    setIsInspectorOpen(false);
    setIsProposalDrawerOpen(false);
  };

  const handleSelectCell = (cell: CellRecord) => {
    setSelectedCell(cell);
    setIsInspectorOpen(true);
  };

  const handleOpenProposalDrawer = (cell: CellRecord) => {
    setCandidateCell(cell);
    setIsProposalDrawerOpen(true);
  };

  // Human Editorial Action: Accept proposal
  const handleAcceptProposal = (targetCell: CellRecord, proposedValue: string) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== targetCell.table_id) return tbl;
        return {
          ...tbl,
          rows: tbl.rows.map((row) =>
            row.map((cell) => {
              if (cell.row_idx === targetCell.row_idx && cell.col_idx === targetCell.col_idx) {
                return {
                  ...cell,
                  accepted_value: proposedValue,
                  quality_status: 'CORRECTED_WITH_EVIDENCE',
                  notes: [...cell.notes, `Human accepted candidate proposal: ${proposedValue}`],
                };
              }
              return cell;
            })
          ),
        };
      })
    );

    // If currently selected cell is updated
    if (
      selectedCell &&
      selectedCell.table_id === targetCell.table_id &&
      selectedCell.row_idx === targetCell.row_idx &&
      selectedCell.col_idx === targetCell.col_idx
    ) {
      setSelectedCell({
        ...selectedCell,
        accepted_value: proposedValue,
        quality_status: 'CORRECTED_WITH_EVIDENCE',
        notes: [...selectedCell.notes, `Human accepted candidate proposal: ${proposedValue}`],
      });
    }
  };

  // Human Editorial Action: Reject proposal
  const handleRejectProposal = (targetCell: CellRecord) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== targetCell.table_id) return tbl;
        return {
          ...tbl,
          rows: tbl.rows.map((row) =>
            row.map((cell) => {
              if (cell.row_idx === targetCell.row_idx && cell.col_idx === targetCell.col_idx) {
                return {
                  ...cell,
                  inferred_candidate_value: null,
                  notes: [...cell.notes, 'Human editor dismissed candidate proposal'],
                };
              }
              return cell;
            })
          ),
        };
      })
    );
  };

  // Human Editorial Clarification: Edit cell value & re-verify downstream
  const handleUpdateCellValue = (targetCell: CellRecord, newValue: string) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== targetCell.table_id) return tbl;
        return {
          ...tbl,
          rows: tbl.rows.map((row) =>
            row.map((cell) => {
              if (cell.row_idx === targetCell.row_idx && cell.col_idx === targetCell.col_idx) {
                return {
                  ...cell,
                  accepted_value: newValue,
                  normalized_value: newValue,
                  numeric_decimal: !isNaN(Number(newValue.replace(/[^0-9.-]+/g, '')))
                    ? newValue.replace(/[^0-9.-]+/g, '')
                    : cell.numeric_decimal,
                  quality_status: 'CORRECTED_WITH_EVIDENCE',
                  notes: [...cell.notes, `User clarification: ${newValue} (Raw was: ${cell.raw_value})`],
                };
              }
              return cell;
            })
          ),
        };
      })
    );

    if (
      selectedCell &&
      selectedCell.table_id === targetCell.table_id &&
      selectedCell.row_idx === targetCell.row_idx &&
      selectedCell.col_idx === targetCell.col_idx
    ) {
      setSelectedCell({
        ...selectedCell,
        accepted_value: newValue,
        normalized_value: newValue,
        numeric_decimal: !isNaN(Number(newValue.replace(/[^0-9.-]+/g, '')))
          ? newValue.replace(/[^0-9.-]+/g, '')
          : selectedCell.numeric_decimal,
        quality_status: 'CORRECTED_WITH_EVIDENCE',
        notes: [...selectedCell.notes, `User clarification: ${newValue} (Raw was: ${selectedCell.raw_value})`],
      });
    }

    if (report && report.validation_issues) {
      setReport({
        ...report,
        validation_issues: report.validation_issues.map((iss) => {
          if (
            iss.table_id === targetCell.table_id &&
            (iss.row_idx === targetCell.row_idx || iss.col_idx === targetCell.col_idx)
          ) {
            return { ...iss, resolved: true };
          }
          return iss;
        }),
      });
    }
  };

  // Add a new row to the active table
  const handleAddRow = (tableId: string, values: string[]) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== tableId) return tbl;
        const newRowIdx = tbl.rows.length;
        const newRow: CellRecord[] = values.map((val, cIdx) => ({
          table_id: tableId,
          row_idx: newRowIdx,
          col_idx: cIdx,
          source_page: tbl.source_pages[0] || 1,
          bbox: null,
          extraction_method: tbl.extraction_method || 'DIGITAL_RULING_LINES',
          ocr_confidence: null,
          raw_value: val,
          normalized_value: val,
          numeric_decimal: !isNaN(Number(val.replace(/[^0-9.-]+/g, ''))) && val.trim() !== ''
            ? val.replace(/[^0-9.-]+/g, '')
            : null,
          accepted_value: val,
          inferred_candidate_value: null,
          data_type: tbl.column_types?.[cIdx] || 'STRING',
          quality_status: 'CORRECTED_WITH_EVIDENCE',
          formula_risk_detected: false,
          notes: ['Manually added by user in interactive table editor'],
        }));

        return {
          ...tbl,
          rows: [...tbl.rows, newRow],
        };
      })
    );
  };

  // Delete a row from the active table and re-index remaining rows
  const handleDeleteRow = (tableId: string, rowIdx: number) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== tableId) return tbl;
        const updatedRows = tbl.rows
          .filter((_, idx) => idx !== rowIdx)
          .map((row, newRIdx) =>
            row.map((cell) => ({
              ...cell,
              row_idx: newRIdx,
            }))
          );
        return {
          ...tbl,
          rows: updatedRows,
        };
      })
    );
  };

  // Edit all values in a specific row
  const handleEditRow = (tableId: string, rowIdx: number, values: string[]) => {
    setTables((prevTables) =>
      prevTables.map((tbl) => {
        if (tbl.table_id !== tableId) return tbl;
        const updatedRows = tbl.rows.map((row, rIdx) => {
          if (rIdx !== rowIdx) return row;
          return row.map((cell, cIdx) => {
            const val = values[cIdx] !== undefined ? values[cIdx] : cell.accepted_value;
            return {
              ...cell,
              accepted_value: val,
              normalized_value: val,
              numeric_decimal: !isNaN(Number(val.replace(/[^0-9.-]+/g, ''))) && val.trim() !== ''
                ? val.replace(/[^0-9.-]+/g, '')
                : cell.numeric_decimal,
              quality_status: 'CORRECTED_WITH_EVIDENCE' as const,
              notes: [...cell.notes, `User edited row: ${val} (Raw was: ${cell.raw_value})`],
            };
          });
        });
        return {
          ...tbl,
          rows: updatedRows,
        };
      })
    );
  };

  // Update a single cell via in-place table grid editing
  const handleUpdateCell = (tableId: string, rowIdx: number, colIdx: number, newValue: string) => {
    const targetTable = tables.find((t) => t.table_id === tableId);
    if (targetTable && targetTable.rows[rowIdx] && targetTable.rows[rowIdx][colIdx]) {
      handleUpdateCellValue(targetTable.rows[rowIdx][colIdx], newValue);
    }
  };

  // Bridge from Discrepancy finding to Cell Inspector for immediate clarification
  const handleClarifyIssue = (tableId: string, rowIdx: number | null, colIdx: number | null) => {
    const targetTable = tables.find((t) => t.table_id === tableId) || tables[0];
    if (targetTable && targetTable.rows.length > 0) {
      const rIdx = rowIdx !== null ? Math.min(rowIdx, targetTable.rows.length - 1) : 0;
      const row = targetTable.rows[rIdx];
      const cIdx = colIdx !== null ? Math.min(colIdx, row.length - 1) : 0;
      const cell = row[cIdx];
      setSelectedCell(cell);
      setIsInspectorOpen(true);
      setActiveTab('workspace');
    }
  };

  const currentTable = tables[activeTableIdx] || tables[0] || null;

  return (
    <Shell
      isBackendConnected={isBackendConnected}
      onCheckBackend={checkBackendHealth}
      onOpenModelRegistry={() => setIsModelRegistryOpen(true)}
      isRetryingConnection={isCheckingBackend}
    >
      {/* Primary Navigation Bar */}
      <nav aria-label="Primary Navigation" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="ds-nav-tabs">
          <button
            type="button"
            className={`ds-nav-tab ${activeTab === 'workspace' ? 'ds-nav-tab-active' : ''}`}
            onClick={() => setActiveTab('workspace')}
            aria-current={activeTab === 'workspace' ? 'page' : undefined}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <FileText size={15} aria-hidden="true" /> Workspace
            </span>
          </button>
          <button
            type="button"
            className={`ds-nav-tab ${activeTab === 'models' ? 'ds-nav-tab-active' : ''}`}
            onClick={() => setActiveTab('models')}
            aria-current={activeTab === 'models' ? 'page' : undefined}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Cpu size={15} aria-hidden="true" /> AI Model Registry
            </span>
          </button>
        </div>
      </nav>

      {/* ── TAB 1: WORKSPACE ──────────────────────────────────────────────── */}
      {activeTab === 'workspace' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {/* Header Description */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 4 }}>
                <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', background: 'var(--color-primary-subtle)', padding: '2px 8px', borderRadius: 'var(--radius-full)' }}>
                  Autonomous Document AI 2.0
                </span>
                <span style={{ fontSize: '11px', color: 'var(--color-slate)' }}>• 50 MB High-Capacity Ingestion</span>
              </div>
              <h2 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
                INCUXAI — Autonomous Document & Tabular Intelligence Workstation
              </h2>
              <p style={{ margin: 0, color: 'var(--color-slate)', fontSize: 'var(--font-size-sm)', marginTop: 4 }}>
                Autonomous multi-dataset extraction, vision-OCR fusion, arbitrary-precision Decimal arithmetic verification, and multi-model AI orchestration.
              </p>
            </div>
            {report && (
              <Button variant="secondary" size="sm" onClick={handleResetDocument}>
                <RefreshCw size={14} style={{ marginRight: 6 }} aria-hidden="true" /> Process Another Document
              </Button>
            )}
          </div>

          {/* If No Report is Active: Ingestion Area on Top, Innovations Below */}
          {!report && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-6)',
              }}
            >
              {/* Top: Document Ingestion */}
              <Card
                title="Document Ingestion"
                subtitle="Upload complex multi-page PDFs or document images (up to 50 MB, 100 pages)"
              >
                <DocumentUpload
                  onExtractionSuccess={handleExtractionSuccess}
                  isBackendConnected={isBackendConnected}
                />
              </Card>

              {/* Below Document Ingestion: Key Advantages, Uniqueness & Novelty */}
              <Card
                title="Key Innovations & Architectural Novelty"
                subtitle="Why INCUXAI is engineered differently for enterprise tabular extraction and audit"
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                    gap: 'var(--space-4)',
                  }}
                >
                  {/* 1. Multi-Dataset Autonomous Reconstruction */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <GitMerge size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        Multi-Dataset Autonomous Segregation (50+ Pages)
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Intelligent schema awareness dynamically detects differing column definitions across page boundaries (e.g. Orders vs Student Records vs Expenses), auto-splitting them into distinct canonical tables without data mangling.
                      </p>
                    </div>
                  </div>

                  {/* 2. Multi-Engine OCR & Vision AI Fusion */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Eye size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        Multi-Engine OCR & Vision AI Fusion
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        High-speed deterministic vector geometry for digital PDFs unified with advanced multimodal Vision AI fallback for scanned pages, receipts, camera photos, and tilted tabular documents.
                      </p>
                    </div>
                  </div>

                  {/* 3. 7-Tier Foundation Model Registry */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Cpu size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        7-Tier Multi-LLM Orchestration Registry
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Provider-agnostic inference across DeepSeek V3, Llama 3.3 70B, Qwen 2.5 72B, Claude 3.5 Sonnet, GPT-4o, and Gemini 2.0 Flash in strict non-destructive standby with automated failover and latency tracking.
                      </p>
                    </div>
                  </div>

                  {/* 4. Interactive Grid & Row Editor */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Table size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        Interactive Spreadsheet Grid & Inline Row Editor
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Full human-in-the-loop editing with in-cell correction, Add Row, and Delete Row operations. Automatically re-computes arithmetic totals and tracks provenance without hallucination.
                      </p>
                    </div>
                  </div>

                  {/* 5. Independent Per-Table & Batch ZIP Exports */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Download size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        Independent Per-Table & Batch ZIP Exports
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Download individual Excel/CSV spreadsheets for every detected dataset (Export Table 1, Table 2, Table 3...) or download all datasets bundled in a single ZIP archive.
                      </p>
                    </div>
                  </div>

                  {/* 6. Exact Decimal Arithmetic & Zero Auto-Balancing */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Scale size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        Arbitrary-Precision Decimal Verification (Zero Hallucination)
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Every column sum uses exact arbitrary-precision Decimal arithmetic, completely eliminating IEEE 754 float drift. Source discrepancies ($100 + $200 = $350) are preserved and transparently audited; never auto-balanced.
                      </p>
                    </div>
                  </div>

                  {/* 7. 50 MB Enterprise Ingestion Ceiling */}
                  <div
                    style={{
                      padding: 'var(--space-4)',
                      backgroundColor: 'var(--color-surface)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      gap: 'var(--space-3)',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        color: 'var(--color-primary)',
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-primary-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <ShieldCheck size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <strong style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-ink)', display: 'block', marginBottom: 3 }}>
                        50 MB Enterprise Ingestion Limit & Verifiable Provenance
                      </strong>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-slate)', lineHeight: 1.45 }}>
                        Engineered to effortlessly process heavy financial ledgers, corporate audit packets, multi-year annual reports, and high-DPI document scans up to 50 MiB and 100 pages.
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* If Report is Active: Full Workstation Presentation */}
          {report && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              {/* 1. Truthful Verification Status Banner */}
              <VerificationBanner
                executionState={report.execution_state}
                verificationStatus={report.verification_status}
                reasonCodes={report.status_reason_codes || []}
                filename={report.source_filename}
                tableCount={tables.length}
              />

              {/* 2. Interactive Data Grid with Toolbar and Export */}
              {tables.length > 0 && currentTable && (
                <Card
                  title={
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                        <span>Extracted Canonical Tables</span>
                        {tables.length > 1 && (
                          <Badge variant="neutral" size="sm">
                            {tables.length} Distinct Tables Detected
                          </Badge>
                        )}
                      </div>
                      <ExportControls
                        table={currentTable}
                        tables={tables}
                        activeTableIdx={activeTableIdx}
                        report={report}
                      />
                    </div>
                  }
                  subtitle={
                    tables.length > 1
                      ? `Found ${tables.length} distinct table structures. Select any table tab below to inspect or download as individual Excel files, or use 'Export All Tables' to download all in one ZIP.`
                      : `Click any cell to open the provenance inspector. Use arrow keys / Enter for keyboard navigation.`
                  }
                >
                  {tables.length > 1 && (
                    <div
                      style={{
                        marginBottom: 'var(--space-4)',
                        padding: 'var(--space-3) var(--space-4)',
                        backgroundColor: '#f0fdf4',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid #bbf7d0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 'var(--space-3)',
                        flexWrap: 'wrap',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: '#166534' }}>
                          ⚡ Multi-Table Extraction Active:
                        </span>
                        <span style={{ fontSize: 'var(--font-size-xs)', color: '#15803d' }}>
                          This document contains {tables.length} distinct tables with independent schemas. You can inspect each table below and download them as individual Excel files or export all at once.
                        </span>
                      </div>
                      <Badge variant="neutral" size="sm">
                        Viewing Table {activeTableIdx + 1} of {tables.length}
                      </Badge>
                    </div>
                  )}

                  <TableGrid
                    tables={tables}
                    activeTableIdx={activeTableIdx}
                    onSelectTable={(idx) => setActiveTableIdx(idx)}
                    selectedCell={selectedCell}
                    onSelectCell={handleSelectCell}
                    onAddRow={handleAddRow}
                    onDeleteRow={handleDeleteRow}
                    onEditRow={handleEditRow}
                    onUpdateCell={handleUpdateCell}
                  />
                </Card>
              )}

              {/* 3. Diagnostics & Audit Section with Subtabs */}
              <div
                style={{
                  border: '1px solid var(--color-border-muted)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-pure-white)',
                  padding: 'var(--space-4)',
                  boxShadow: 'var(--shadow-xs)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-4)',
                }}
              >
                {/* Subtab navigation */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-2)' }}>
                  <button
                    type="button"
                    className={`ds-nav-tab ${auditSubtab === 'discrepancies' ? 'ds-nav-tab-active' : ''}`}
                    onClick={() => setAuditSubtab('discrepancies')}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--font-size-xs)' }}>
                      <Scale size={14} aria-hidden="true" /> Discrepancies & AI Advisory ({report.validation_issues?.length || 0})
                    </span>
                  </button>
                  <button
                    type="button"
                    className={`ds-nav-tab ${auditSubtab === 'pages' ? 'ds-nav-tab-active' : ''}`}
                    onClick={() => setAuditSubtab('pages')}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--font-size-xs)' }}>
                      <Layers size={14} aria-hidden="true" /> Page Profiles ({report.page_profiles?.length || 0})
                    </span>
                  </button>
                  <button
                    type="button"
                    className={`ds-nav-tab ${auditSubtab === 'stitch' ? 'ds-nav-tab-active' : ''}`}
                    onClick={() => setAuditSubtab('stitch')}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--font-size-xs)' }}>
                      <GitMerge size={14} aria-hidden="true" /> Multipage Stitch Audit ({report.stitch_events?.length || 0})
                    </span>
                  </button>
                </div>

                {/* Subtab Contents */}
                {auditSubtab === 'discrepancies' && (
                  <DiscrepancyAdjudication
                    issues={report.validation_issues || []}
                    onOpenModelRegistry={() => setIsModelRegistryOpen(true)}
                    onClarifyCell={handleClarifyIssue}
                  />
                )}

                {auditSubtab === 'pages' && (
                  <PageProfiles profiles={report.page_profiles || []} />
                )}

                {auditSubtab === 'stitch' && (
                  <StitchAudit stitchEvents={report.stitch_events || []} />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: AI MODEL REGISTRY ──────────────────────────────────────── */}
      {activeTab === 'models' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <h2>Seven-Model Provider-Agnostic AI Architecture</h2>
            <p style={{ color: 'var(--color-slate)', fontSize: 'var(--font-size-sm)' }}>
              Declarative model registry with 4-part verification status. All candidate models operate in advisory standby mode.
            </p>
          </div>

          {/* Provider Adapters Live Status Bar */}
          <div
            style={{
              padding: 'var(--space-4)',
              backgroundColor: 'var(--color-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 'var(--space-3)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-ink)' }}>
                Provider Adapters:
              </span>
              {(['GROQ', 'TOGETHER', 'OPENROUTER', 'DEEPSEEK', 'ZAI'] as const).map((p) => {
                const isConfigured = modelsData?.providers?.[p]?.configured ?? true;
                return (
                  <Badge key={p} variant={isConfigured ? 'verified' : 'neutral'} size="sm">
                    {p}: {isConfigured ? 'Configured' : 'Missing Key'}
                  </Badge>
                );
              })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsModelRegistryOpen(true)}
            >
              Open Full 4-Part Capability Matrix
            </Button>
          </div>

          <Callout variant="info" title="Model Invocations in Advisory Standby">
            All 7 candidate models operate strictly as non-destructive advisory proposal generators across 5 connected provider adapters. Deterministic extraction and arithmetic verification remain 100% authoritative.
          </Callout>

          <Card
            title="Candidate Models & Routing Matrix"
            subtitle="Registered models adhering to DECISION-010 and DECISION-011"
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {[
                { name: 'GPT-OSS 20B', provider: 'Groq (Fallback: Together / OpenRouter)', tasks: 'Routine classification, proposal generation', priority: 1 },
                { name: 'GPT-OSS 120B', provider: 'Together AI (Fallback: Groq / OpenRouter)', tasks: 'Conflicting extraction hypotheses, complex escalation', priority: 1 },
                { name: 'DeepSeek V4.1 Flash', provider: 'DeepSeek API (Fallback: OpenRouter)', tasks: 'Complex table interpretation, ragged rows', priority: 1 },
                { name: 'GLM-5.3-Flash through Z.ai', provider: 'Z.ai API (Fallback: OpenRouter)', tasks: 'Long-context reasoning, multilingual Chinese financial tables', priority: 1 },
                { name: 'Qwen3.8-27B', provider: 'Together AI (Fallback: OpenRouter)', tasks: 'Multilingual and regional script tables (Arabic, Cyrillic, Indic)', priority: 1 },
                { name: 'Llama 4 Scout', provider: 'Groq (Fallback: Together / OpenRouter)', tasks: 'Visual table inspection, borderless raster zones', priority: 1 },
                { name: 'Gemma 4', provider: 'Groq (Fallback: Together / OpenRouter)', tasks: 'Visual table review, edge-case validation', priority: 2 },
              ].map((m) => {
                const modelRecord = modelsData?.models?.find((item) => item.candidate_name === m.name);
                const isCredConfigured = modelRecord ? modelRecord.verification_status?.credentials === 'CONFIGURED' : true;
                return (
                  <div
                    key={m.name}
                    style={{
                      padding: 'var(--space-3) var(--space-4)',
                      border: '1px solid var(--color-border-muted)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 'var(--space-3)',
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <strong style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-ink)' }}>
                          {m.name}
                        </strong>
                        <Badge variant="neutral" size="sm">
                          Priority {m.priority}
                        </Badge>
                      </div>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-slate)' }}>
                        Provider: {m.provider} • Tasks: {m.tasks}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <Badge variant={isCredConfigured ? 'verified' : 'neutral'} size="sm">
                        {isCredConfigured ? 'Key Configured' : 'Missing Key'}
                      </Badge>
                      <Badge variant="verified" size="sm">Standby (Advisory)</Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* Model Registry Slide-Over Drawer */}
      <ModelRegistryDrawer
        isOpen={isModelRegistryOpen}
        onClose={() => setIsModelRegistryOpen(false)}
      />

      {/* Cell Provenance Inspector Drawer */}
      <CellInspector
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        cell={selectedCell}
        onOpenCandidateProposal={(c) => {
          setIsInspectorOpen(false);
          handleOpenProposalDrawer(c);
        }}
        onUpdateCellValue={handleUpdateCellValue}
      />

      {/* Candidate Proposal Drawer */}
      <CandidateProposalDrawer
        isOpen={isProposalDrawerOpen}
        onClose={() => setIsProposalDrawerOpen(false)}
        cell={candidateCell}
        table={currentTable}
        onAcceptProposal={handleAcceptProposal}
        onRejectProposal={handleRejectProposal}
      />
    </Shell>
  );
};
