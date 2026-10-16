import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CandidateProposalDrawer, DiscrepancyAdjudication } from '../ai';
import type { CellRecord, CanonicalTable, ValidationIssue } from '../../types/domain';

const mockCell: CellRecord = {
  table_id: 'tbl_advisory',
  row_idx: 1,
  col_idx: 1,
  source_page: 1,
  bbox: null,
  extraction_method: 'DIGITAL_RULING_LINES',
  ocr_confidence: null,
  raw_value: '35O.00',
  normalized_value: '35O.00',
  numeric_decimal: null,
  accepted_value: '35O.00',
  inferred_candidate_value: '350.00',
  data_type: 'STRING',
  quality_status: 'ILLEGIBLE_OR_MISSING',
  formula_risk_detected: false,
  notes: ['OCR character confusion: letter O instead of digit 0'],
};

const mockTable: CanonicalTable = {
  table_id: 'tbl_advisory',
  title: 'Revenue Audit',
  source_pages: [1],
  page_bbox: null,
  original_headers: ['Item', 'Amount'],
  normalized_headers: ['Item', 'Amount'],
  header_row_count: 1,
  column_types: ['STRING', 'DECIMAL'],
  column_semantic_roles: [],
  rows: [
    [
      { ...mockCell, row_idx: 0, col_idx: 0, raw_value: 'Service A', accepted_value: 'Service A' },
      { ...mockCell, row_idx: 0, col_idx: 1, raw_value: '100.00', accepted_value: '100.00' },
    ],
    [
      { ...mockCell, row_idx: 1, col_idx: 0, raw_value: 'Service B', accepted_value: 'Service B' },
      mockCell,
    ],
  ],
  extraction_method: 'DIGITAL_RULING_LINES',
  stitch_events: [],
  validation_issues: [],
  correction_records: [
    {
      audit_id: 'corr_1',
      table_id: 'tbl_advisory',
      source_page: 1,
      row_idx: 1,
      col_idx: 1,
      original_raw_value: '35O.00',
      proposed_value: '350.00',
      accepted_value: '35O.00',
      inferred_candidate_only: false,
      evidence_source: 'NATIVE_PDF_CHAR_STREAM',
      evidence_summary: 'Char stream reveals digit 0 bounding box coordinates.',
      deterministic_check_passed: true,
      decision: 'PROPOSAL_GENERATED',
      resulting_cell_status: 'CORRECTED_WITH_EVIDENCE',
    },
  ],
  structural_checks_passed: true,
  math_validation_outcome: 'PASSED_WITH_WARNINGS',
  verification_status: 'VERIFIED_WITH_WARNINGS',
};

describe('CandidateProposalDrawer Component', () => {
  it('renders raw and proposed values with traceable evidence', () => {
    render(
      <CandidateProposalDrawer
        isOpen={true}
        onClose={vi.fn()}
        cell={mockCell}
        table={mockTable}
      />
    );

    expect(screen.getByTestId('proposal-raw-value')).toHaveTextContent('35O.00');
    expect(screen.getByTestId('proposal-candidate-value')).toHaveTextContent('350.00');
    expect(screen.getByText('NATIVE_PDF_CHAR_STREAM')).toBeInTheDocument();
    expect(
      screen.getByText(/Char stream reveals digit 0 bounding box coordinates/i)
    ).toBeInTheDocument();
  });

  it('allows human acceptance of proposal on non-total cell', () => {
    const handleAccept = vi.fn();
    render(
      <CandidateProposalDrawer
        isOpen={true}
        onClose={vi.fn()}
        cell={mockCell}
        table={mockTable}
        onAcceptProposal={handleAccept}
      />
    );

    const acceptBtn = screen.getByTestId('accept-proposal-btn');
    expect(acceptBtn).toBeEnabled();

    fireEvent.click(acceptBtn);
    expect(handleAccept).toHaveBeenCalledWith(mockCell, '350.00');
  });

  it('strictly prohibits auto-balancing on total/summary row cells', () => {
    const totalRowCell: CellRecord = {
      ...mockCell,
      row_idx: 2,
      raw_value: '350.00',
      accepted_value: '350.00',
      inferred_candidate_value: '300.00',
    };

    const tableWithTotal: CanonicalTable = {
      ...mockTable,
      rows: [
        ...mockTable.rows,
        [
          { ...mockCell, row_idx: 2, col_idx: 0, raw_value: 'Total', accepted_value: 'Total' },
          totalRowCell,
        ],
      ],
    };

    render(
      <CandidateProposalDrawer
        isOpen={true}
        onClose={vi.fn()}
        cell={totalRowCell}
        table={tableWithTotal}
      />
    );

    // Auto-balancing prohibition callout must be shown
    expect(
      screen.getByTestId('autobalance-prohibition-warning')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Auto-Balancing Prohibited \(DECISION-007 & DECISION-011\)/i)
    ).toBeInTheDocument();

    // Accept button must be disabled
    const acceptBtn = screen.getByTestId('accept-proposal-btn');
    expect(acceptBtn).toBeDisabled();
    expect(acceptBtn).toHaveTextContent(/Accept Blocked \(Total Row\)/i);
  });
});

describe('DiscrepancyAdjudication Component', () => {
  const mockIssues: ValidationIssue[] = [
    {
      issue_id: 'iss_1',
      table_id: 'tbl_math',
      source_page: 1,
      row_idx: 2,
      col_idx: 1,
      issue_code: 'SOURCE_ARITHMETIC_DISCREPANCY',
      severity: 'WARNING',
      description: 'Calculated row sum does not match printed table total.',
      expected_value: '300.00',
      actual_value: '350.00',
      resolved: false,
    },
  ];

  it('truthfully presents AI model advisory status as standby / unverified', () => {
    render(<DiscrepancyAdjudication issues={mockIssues} />);

    expect(
      screen.getByText(/Multi-LLM Advisory Status: Standby \/ Unverified/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/All 7 candidate models currently remain disabled, unverified, and non-operational/i)
    ).toBeInTheDocument();
  });

  it('renders discrepancy details, math comparison, and permits acknowledgement', () => {
    const handleToggle = vi.fn();
    render(
      <DiscrepancyAdjudication issues={mockIssues} onToggleResolve={handleToggle} />
    );

    expect(screen.getByText('SOURCE_ARITHMETIC_DISCREPANCY')).toBeInTheDocument();
    expect(screen.getByText('350.00')).toBeInTheDocument();
    expect(screen.getByText('300.00')).toBeInTheDocument();

    const ackBtn = screen.getByRole('button', { name: /Acknowledge Discrepancy/i });
    fireEvent.click(ackBtn);

    expect(handleToggle).toHaveBeenCalledWith('iss_1');
    expect(screen.getByRole('button', { name: /Re-open Finding/i })).toBeInTheDocument();
  });
});
