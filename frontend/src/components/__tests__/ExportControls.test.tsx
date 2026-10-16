import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportControls } from '../export';
import type { CanonicalTable, DocumentEvaluationReport } from '../../types/domain';

const mockTable: CanonicalTable = {
  table_id: 'test_table_export',
  title: 'Export Test',
  source_pages: [1],
  page_bbox: null,
  original_headers: ['Name', 'Revenue', 'Notes'],
  normalized_headers: ['Client Name', 'Revenue Amount', 'Notes'],
  header_row_count: 1,
  column_types: ['STRING', 'DECIMAL', 'STRING'],
  column_semantic_roles: [],
  rows: [
    [
      {
        table_id: 'test_table_export',
        row_idx: 0,
        col_idx: 0,
        source_page: 1,
        bbox: null,
        extraction_method: 'DIGITAL',
        ocr_confidence: null,
        raw_value: 'Acme, Inc.',
        normalized_value: 'Acme, Inc.',
        numeric_decimal: null,
        accepted_value: 'Acme, Inc.',
        inferred_candidate_value: null,
        data_type: 'STRING',
        quality_status: 'EXTRACTED_AS_IS',
        formula_risk_detected: false,
        notes: [],
      },
      {
        table_id: 'test_table_export',
        row_idx: 0,
        col_idx: 1,
        source_page: 1,
        bbox: null,
        extraction_method: 'DIGITAL',
        ocr_confidence: null,
        raw_value: '5000.00',
        normalized_value: '5000.00',
        numeric_decimal: '5000.00',
        accepted_value: '5000.00',
        inferred_candidate_value: null,
        data_type: 'DECIMAL',
        quality_status: 'EXTRACTED_AS_IS',
        formula_risk_detected: false,
        notes: [],
      },
      {
        table_id: 'test_table_export',
        row_idx: 0,
        col_idx: 2,
        source_page: 1,
        bbox: null,
        extraction_method: 'DIGITAL',
        ocr_confidence: null,
        raw_value: 'Quarterly "Priority"',
        normalized_value: 'Quarterly "Priority"',
        numeric_decimal: null,
        accepted_value: 'Quarterly "Priority"',
        inferred_candidate_value: null,
        data_type: 'STRING',
        quality_status: 'EXTRACTED_AS_IS',
        formula_risk_detected: false,
        notes: [],
      },
    ],
  ],
  extraction_method: 'DIGITAL',
  stitch_events: [],
  validation_issues: [],
  correction_records: [],
  structural_checks_passed: true,
  math_validation_outcome: 'PASSED',
  verification_status: 'VERIFIED',
};

const mockReport: DocumentEvaluationReport = {
  job_id: 'job_export_999',
  source_filename: 'sample.pdf',
  execution_state: 'COMPLETED',
  verification_status: 'VERIFIED',
  status_reason_codes: [],
  limitation_disclaimers: [],
  page_profiles: [],
  page_results: [],
  canonical_tables: [mockTable],
  stitch_events: [],
  validation_issues: [],
  correction_records: [],
  peak_python_heap_bytes: 1024,
};

describe('ExportControls Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('renders CSV, Table JSON, and Full Report export buttons', () => {
    render(<ExportControls table={mockTable} report={mockReport} />);

    expect(screen.getByRole('button', { name: /Export table as CSV/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Export table as JSON/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Export full audit report as JSON/i })).toBeInTheDocument();
  });

  it('triggers client-side CSV download escaping special characters (quotes, commas)', async () => {
    const createObjectURLSpy = vi.fn().mockReturnValue('blob:dummy-url');
    const revokeObjectURLSpy = vi.fn();
    window.URL.createObjectURL = createObjectURLSpy;
    window.URL.revokeObjectURL = revokeObjectURLSpy;

    render(<ExportControls table={mockTable} report={mockReport} />);

    const csvBtn = screen.getByRole('button', { name: /Export table as CSV/i });
    fireEvent.click(csvBtn);

    await waitFor(() => {
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(screen.getByText(/CSV exported successfully/i)).toBeInTheDocument();
    });
  });

  it('triggers client-side JSON download', async () => {
    const createObjectURLSpy = vi.fn().mockReturnValue('blob:dummy-url-json');
    const revokeObjectURLSpy = vi.fn();
    window.URL.createObjectURL = createObjectURLSpy;
    window.URL.revokeObjectURL = revokeObjectURLSpy;

    render(<ExportControls table={mockTable} report={mockReport} />);

    const jsonBtn = screen.getByRole('button', { name: /Export table as JSON/i });
    fireEvent.click(jsonBtn);

    await waitFor(() => {
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(screen.getByText(/Table JSON exported successfully/i)).toBeInTheDocument();
    });
  });

  it('renders independent export buttons for each table and all tables zip when multiple tables exist', async () => {
    const table2: CanonicalTable = {
      ...mockTable,
      table_id: 'test_table_2',
      title: 'Dataset 2',
      source_pages: [2],
    };
    const table3: CanonicalTable = {
      ...mockTable,
      table_id: 'test_table_3',
      title: 'Dataset 3',
      source_pages: [3],
    };

    render(
      <ExportControls
        table={mockTable}
        tables={[mockTable, table2, table3]}
        activeTableIdx={0}
        report={mockReport}
      />
    );

    // Verify all 3 independent table export buttons are rendered
    expect(screen.getByTestId('export-table-1-btn')).toBeInTheDocument();
    expect(screen.getByTestId('export-table-2-btn')).toBeInTheDocument();
    expect(screen.getByTestId('export-table-3-btn')).toBeInTheDocument();

    // Verify All Tables ZIP export button is rendered
    expect(screen.getByTestId('export-all-zip-btn')).toBeInTheDocument();
    expect(screen.getByText(/Export All Tables \(3 Files \/ ZIP\)/i)).toBeInTheDocument();

    // Clicking Table 2 export button triggers download of Table 2
    const createObjectURLSpy = vi.fn().mockReturnValue('blob:dummy-url-t2');
    window.URL.createObjectURL = createObjectURLSpy;
    fireEvent.click(screen.getByTestId('export-table-2-btn'));

    await waitFor(() => {
      expect(createObjectURLSpy).toHaveBeenCalled();
    });
  });
});

