import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../../App';
import { apiClient } from '../../api/client';
import type {
  DocumentEvaluationReport,
  CanonicalTable,
  CellRecord,
} from '../../types/domain';

// Mock the apiClient for deterministic E2E simulation
vi.mock('../../api/client', () => {
  return {
    apiClient: {
      checkHealth: vi.fn().mockResolvedValue({
        status: 'healthy',
        version: '1.0.0',
        backend_ready: true,
      }),
      getModelsStatus: vi.fn().mockResolvedValue({
        models: [
          {
            candidate_name: 'GPT-OSS 20B',
            exact_model_id: 'gpt-oss-20b',
            provider: 'GROQ',
            modalities: ['TEXT'],
            tasks: ['ROUTINE_EXTRACTION_CLASSIFICATION'],
            config_key: 'GROQ_API_KEY',
            enabled_state: false,
            verification_status: {
              existence: 'UNVERIFIED',
              availability: 'UNCHECKED',
              credentials: 'MISSING_CREDENTIALS',
              test_result: 'UNTESTED',
            },
            routing_priority: 1,
            timeout_seconds: 30,
            max_retries: 2,
            fallback_eligible: true,
            last_test_timestamp: null,
            notes: 'Standby candidate',
          },
        ],
        providers: {
          GROQ: { status: 'HEALTHY', provider: 'GROQ', latency_ms: 25 },
        },
        timestamp: '2026-10-15T12:00:00Z',
      }),
      extractDocument: vi.fn(),
      exportCsv: vi.fn(),
      exportJson: vi.fn(),
    },
    MAX_FILE_SIZE_BYTES: 52_428_800,
  };
});

describe('DocuStruct AI — End-to-End Workstation Workflows', () => {
  const mockCellA: CellRecord = {
    table_id: 'tbl-e2e-1',
    row_idx: 0,
    col_idx: 0,
    source_page: 1,
    bbox: {
      x0: 50,
      y0: 100,
      x1: 150,
      y1: 120,
      page_width: 612,
      page_height: 792,
      coord_exact: true,
      norm_x0: 0.08,
      norm_x1: 0.25,
      norm_y0: 0.13,
      norm_y1: 0.15,
    },
    extraction_method: 'DIGITAL_LINE_GEOMETRY',
    ocr_confidence: null,
    raw_value: 'Consulting Services',
    normalized_value: 'Consulting Services',
    numeric_decimal: null,
    accepted_value: 'Consulting Services',
    inferred_candidate_value: null,
    data_type: 'STRING',
    quality_status: 'EXTRACTED_AS_IS',
    formula_risk_detected: false,
    notes: [],
  };

  const mockCellB: CellRecord = {
    table_id: 'tbl-e2e-1',
    row_idx: 0,
    col_idx: 1,
    source_page: 1,
    bbox: {
      x0: 200,
      y0: 100,
      x1: 280,
      y1: 120,
      page_width: 612,
      page_height: 792,
      coord_exact: true,
      norm_x0: 0.33,
      norm_x1: 0.46,
      norm_y0: 0.13,
      norm_y1: 0.15,
    },
    extraction_method: 'DIGITAL_LINE_GEOMETRY',
    ocr_confidence: null,
    raw_value: '$1,500.00',
    normalized_value: '1500.00',
    numeric_decimal: '1500.00',
    accepted_value: '$1,500.00',
    inferred_candidate_value: '$1,550.00',
    data_type: 'DECIMAL',
    quality_status: 'EXTRACTED_AS_IS',
    formula_risk_detected: false,
    notes: [],
  };

  const mockTotalRowHeader: CellRecord = {
    ...mockCellA,
    row_idx: 1,
    raw_value: 'Total Revenue',
    accepted_value: 'Total Revenue',
  };

  const mockTotalCell: CellRecord = {
    ...mockCellB,
    row_idx: 1,
    raw_value: '$1,500.00',
    accepted_value: '$1,500.00',
    inferred_candidate_value: '$1,550.00',
  };

  const mockCanonicalTable: CanonicalTable = {
    table_id: 'tbl-e2e-1',
    title: 'Operating Statement Table 1',
    source_pages: [1],
    page_bbox: null,
    original_headers: ['Description', 'Net Amount'],
    normalized_headers: ['Description', 'Net Amount'],
    header_row_count: 1,
    column_types: ['STRING', 'DECIMAL'],
    column_semantic_roles: ['LABEL', 'DATA'],
    rows: [
      [mockCellA, mockCellB],
      [mockTotalRowHeader, mockTotalCell],
    ],
    extraction_method: 'DIGITAL_LINE_GEOMETRY',
    stitch_events: [],
    validation_issues: [],
    structural_checks_passed: true,
    math_validation_outcome: 'PASSED',
    verification_status: 'VERIFIED',
    correction_records: [
      {
        audit_id: 'audit-e2e-1',
        table_id: 'tbl-e2e-1',
        source_page: 1,
        row_idx: 0,
        col_idx: 1,
        original_raw_value: '$1,500.00',
        proposed_value: '$1,550.00',
        accepted_value: '$1,500.00',
        evidence_source: 'VECTOR_GRID_GEOMETRY',
        evidence_summary: 'Aligned ruling coordinate and boundary verification.',
        deterministic_check_passed: true,
        decision: 'PROPOSED_PENDING_CONFIRMATION',
        resulting_cell_status: 'CORRECTED_WITH_EVIDENCE',
        inferred_candidate_only: false,
      },
      {
        audit_id: 'audit-e2e-2',
        table_id: 'tbl-e2e-1',
        source_page: 1,
        row_idx: 1,
        col_idx: 1,
        original_raw_value: '$1,500.00',
        proposed_value: '$1,550.00',
        accepted_value: '$1,500.00',
        evidence_source: 'VECTOR_GRID_GEOMETRY',
        evidence_summary: 'Discrepancy detected with summary column.',
        deterministic_check_passed: false,
        decision: 'REJECTED_AUTO_BALANCE_PRESERVED_RAW',
        resulting_cell_status: 'EXTRACTED_AS_IS',
        inferred_candidate_only: true,
      },
    ],
  };

  const mockSuccessfulReport: DocumentEvaluationReport = {
    job_id: 'job-e2e-101',
    source_filename: 'financial_audit_2026.pdf',
    execution_state: 'COMPLETED',
    verification_status: 'VERIFIED',
    status_reason_codes: [],
    limitation_disclaimers: [],
    page_profiles: [
      {
        page_number: 1,
        page_type: 'DIGITAL',
        processing_status: 'EXTRACTED',
        printable_char_count: 850,
        garbled_char_ratio: 0.0,
        image_coverage_ratio: 0.02,
        vector_line_count: 36,
        deferred_regions_count: 0,
        table_presence: 'CONFIRMED_PRESENT',
      },
    ],
    page_results: [],
    canonical_tables: [mockCanonicalTable],
    stitch_events: [],
    validation_issues: [],
    correction_records: [],
    peak_python_heap_bytes: 14_000_000,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock URL methods for exports
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-blob-id');
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  it('executes full end-to-end extraction workflow and renders results with verbatim disclaimer', async () => {
    vi.mocked(apiClient.extractDocument).mockResolvedValueOnce(mockSuccessfulReport);

    render(<App />);

    // 1. Verify idle dropzone is displayed
    expect(screen.getAllByText(/Upload PDF for Deterministic Extraction/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Max Size: 50 MiB/i)).toBeInTheDocument();

    // 2. Select a PDF file
    const file = new File(['%PDF-1.4 test stream content'], 'financial_audit_2026.pdf', {
      type: 'application/pdf',
    });
    const fileInput = screen.getByTestId('file-input');
    fireEvent.change(fileInput, { target: { files: [file] } });

    // 3. Verify selected file card and trigger extraction
    expect(screen.getByText('financial_audit_2026.pdf')).toBeInTheDocument();
    const runBtn = screen.getByRole('button', { name: /Run Extraction/i });
    fireEvent.click(runBtn);

    // 4. Verify API call was made with the selected file
    expect(apiClient.extractDocument).toHaveBeenCalledTimes(1);
    expect(apiClient.extractDocument).toHaveBeenCalledWith(file, expect.any(AbortSignal));

    // 5. Await results: Verification Banner and Verbatim Disclaimer
    await waitFor(() => {
      expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Verified: Structural Integrity & Arithmetic Validated/i)
    ).toBeInTheDocument();

    // Mandatory verbatim disclaimer check
    const disclaimer = screen.getByTestId('verbatim-disclaimer');
    expect(disclaimer).toBeInTheDocument();
    expect(disclaimer).toHaveTextContent(
      'Structural integrity and internal arithmetic consistency were verified. ' +
        'This does not independently prove every source cell is correct and cannot ' +
        'rule out offsetting cell errors or errors in non-numeric text.'
    );

    // 6. Verify table grid rendering
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Net Amount')).toBeInTheDocument();
    expect(screen.getByText('Consulting Services')).toBeInTheDocument();
    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
  });

  it('allows cell inspection, displaying unalterable raw source evidence and bounding box', async () => {
    vi.mocked(apiClient.extractDocument).mockResolvedValueOnce(mockSuccessfulReport);

    render(<App />);

    // Ingest file
    const file = new File(['%PDF-1.4 dummy'], 'audit.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Run Extraction/i }));

    await waitFor(() => {
      expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    });

    // Click Consulting Services cell to open CellInspector
    const cellElement = screen.getByText('Consulting Services').closest('td');
    expect(cellElement).not.toBeNull();
    fireEvent.click(cellElement!);

    // Verify CellInspector drawer opened
    await waitFor(() => {
      expect(screen.getByTestId('cell-inspector-panel')).toBeInTheDocument();
    });

    // Check Immutable Raw Value labeled as Unalterable Source Evidence
    expect(screen.getByText(/Unalterable Source Evidence/i)).toBeInTheDocument();
    expect(screen.getByTestId('cell-raw-value')).toHaveTextContent('Consulting Services');
    expect(screen.getByTestId('cell-accepted-value')).toHaveTextContent('Consulting Services');

    // Check Bounding box coordinates display in points
    expect(screen.getByText('x0:')).toBeInTheDocument();
    expect(screen.getByText('50.00 pt')).toBeInTheDocument();
    expect(screen.getByText('y0:')).toBeInTheDocument();
    expect(screen.getByText('100.00 pt')).toBeInTheDocument();

    // Close drawer via Escape key
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByTestId('cell-inspector-panel')).not.toBeInTheDocument();
    });
  });

  it('enforces auto-balancing prohibition on total rows and blocks proposal acceptance', async () => {
    vi.mocked(apiClient.extractDocument).mockResolvedValueOnce(mockSuccessfulReport);

    render(<App />);

    const file = new File(['%PDF-1.4 dummy'], 'audit.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Run Extraction/i }));

    await waitFor(() => {
      expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    });

    // Row 1 (Total Revenue row) has mockTotalCell which is on a Total row
    const totalRow = screen.getByTestId('table-row-1');
    const totalAmountCell = totalRow.querySelectorAll('td')[1];
    fireEvent.click(totalAmountCell);

    // Open proposal drawer from cell inspector
    await waitFor(() => {
      expect(screen.getByTestId('cell-inspector-panel')).toBeInTheDocument();
    });

    const reviewBtn = screen.getByRole('button', { name: /Review Evidence & Proposal/i });
    fireEvent.click(reviewBtn);

    // Verify Candidate Proposal Drawer opened
    await waitFor(() => {
      expect(screen.getByTestId('candidate-proposal-drawer')).toBeInTheDocument();
    });

    // Verify Auto-Balancing Prohibition Warning is displayed
    const warning = screen.getByTestId('autobalance-prohibition-warning');
    expect(warning).toBeInTheDocument();
    expect(warning).toHaveTextContent(/Auto-Balancing Prohibited \(DECISION-007 & DECISION-011\)/i);

    // Verify Accept button is hard-blocked and disabled
    const acceptBtn = screen.getByTestId('accept-proposal-btn');
    expect(acceptBtn).toBeDisabled();
    expect(acceptBtn).toHaveTextContent(/Accept Blocked \(Total Row\)/i);
  });

  it('accepts candidate proposal on valid non-total cell in session-only state without mutating raw_value', async () => {
    vi.mocked(apiClient.extractDocument).mockResolvedValueOnce(mockSuccessfulReport);

    render(<App />);

    const file = new File(['%PDF-1.4 dummy'], 'audit.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Run Extraction/i }));

    await waitFor(() => {
      expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    });

    // Row 0, Col 1 is mockCellB (non-total cell with proposal $1,550.00)
    const row0 = screen.getByTestId('table-row-0');
    const cellB = row0.querySelectorAll('td')[1];
    fireEvent.click(cellB);

    await waitFor(() => {
      expect(screen.getByTestId('cell-inspector-panel')).toBeInTheDocument();
    });

    const reviewBtn = screen.getByRole('button', { name: /Review Evidence & Proposal/i });
    fireEvent.click(reviewBtn);

    await waitFor(() => {
      expect(screen.getByTestId('candidate-proposal-drawer')).toBeInTheDocument();
    });

    // Accept button should be enabled on non-total cell
    const acceptBtn = screen.getByTestId('accept-proposal-btn');
    expect(acceptBtn).not.toBeDisabled();
    expect(acceptBtn).toHaveTextContent(/Accept as Accepted Value/i);

    // Accept proposal
    fireEvent.click(acceptBtn);

    // Verify cell now shows accepted proposal value in TableGrid
    await waitFor(() => {
      const updatedRow0 = screen.getByTestId('table-row-0');
      expect(updatedRow0.querySelectorAll('td')[1]).toHaveTextContent('$1,550.00');
    });

    // Click cell again to inspect raw_value
    const updatedCell = screen.getByTestId('table-row-0').querySelectorAll('td')[1];
    fireEvent.click(updatedCell);

    await waitFor(() => {
      expect(screen.getByTestId('cell-inspector-panel')).toBeInTheDocument();
    });

    // raw_value MUST remain strictly uncorrupted $1,500.00
    expect(screen.getByTestId('cell-raw-value')).toHaveTextContent('$1,500.00');
    expect(screen.getByTestId('cell-accepted-value')).toHaveTextContent('$1,550.00');

    // Verify NO server mutation endpoints were called (session-only invariant)
    expect(apiClient.exportCsv).not.toHaveBeenCalled();
    expect(apiClient.exportJson).not.toHaveBeenCalled();
  });

  it('performs client-side CSV and JSON export with object URL cleanup', async () => {
    vi.mocked(apiClient.extractDocument).mockResolvedValueOnce(mockSuccessfulReport);

    render(<App />);

    const file = new File(['%PDF-1.4 dummy'], 'audit.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Run Extraction/i }));

    await waitFor(() => {
      expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    });

    const exportSection = screen.getByTestId('export-controls');
    expect(exportSection).toBeInTheDocument();

    // Export CSV
    const csvBtn = screen.getByRole('button', { name: /Export table as CSV/i });
    fireEvent.click(csvBtn);

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-blob-id');

    // Export Table JSON
    const jsonBtn = screen.getByRole('button', { name: /Export table as JSON/i });
    fireEvent.click(jsonBtn);

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledTimes(2);
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledTimes(2);
  });

  it('handles cancellation and allows re-initiating extraction', async () => {
    vi.mocked(apiClient.extractDocument).mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(resolve, 5000))
    );

    render(<App />);

    const file = new File(['%PDF-1.4 dummy'], 'pending.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Run Extraction/i }));

    // Verify processing state
    expect(screen.getByText(/Executing ruling-line geometry analysis/i)).toBeInTheDocument();
    const cancelBtn = screen.getByRole('button', { name: /Cancel Extraction/i });
    expect(cancelBtn).toBeInTheDocument();

    // Cancel extraction
    fireEvent.click(cancelBtn);

    // Verify file card is restored with Run Extraction ready for retry
    expect(screen.getByText('pending.pdf')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Extraction/i })).toBeInTheDocument();
  });
});
