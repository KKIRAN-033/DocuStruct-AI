import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CellInspector } from '../table';
import type { CellRecord } from '../../types/domain';

const mockCell: CellRecord = {
  table_id: 'table_audit_1',
  row_idx: 3,
  col_idx: 2,
  source_page: 2,
  bbox: {
    x0: 45.5,
    y0: 120.25,
    x1: 155.0,
    y1: 142.5,
    page_width: 612,
    page_height: 792,
    coord_exact: true,
    norm_x0: 0.074,
    norm_x1: 0.253,
    norm_y0: 0.151,
    norm_y1: 0.179,
  },
  extraction_method: 'DIGITAL_RULING_LINES',
  ocr_confidence: null,
  raw_value: '$1,250.50',
  normalized_value: '1250.50',
  numeric_decimal: '1250.50',
  accepted_value: '1250.50',
  inferred_candidate_value: null,
  data_type: 'DECIMAL',
  quality_status: 'EXTRACTED_AS_IS',
  formula_risk_detected: false,
  notes: ['Normalizer parsed standard thousands grouping'],
};

describe('CellInspector Component', () => {
  it('renders cell coordinates, immutable raw value, and accepted value', () => {
    render(<CellInspector isOpen={true} onClose={vi.fn()} cell={mockCell} />);

    expect(screen.getByText(/Cell Provenance & Inspection/i)).toBeInTheDocument();
    expect(screen.getByText('R4 : C3')).toBeInTheDocument();
    expect(screen.getByText('Table: table_audit_1 (Page 2)')).toBeInTheDocument();

    const rawEl = screen.getByTestId('cell-raw-value');
    expect(rawEl).toHaveTextContent('$1,250.50');

    const acceptedEl = screen.getByTestId('cell-accepted-value');
    expect(acceptedEl).toHaveTextContent('1250.50');

    expect(screen.getAllByText('1250.50').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/45.50 pt/i)).toBeInTheDocument();
    expect(screen.getByText(/120.25 pt/i)).toBeInTheDocument();
  });

  it('renders formula risk warning when formula risk is detected', () => {
    const formulaCell: CellRecord = {
      ...mockCell,
      raw_value: '+100.00',
      formula_risk_detected: true,
    };

    render(<CellInspector isOpen={true} onClose={vi.fn()} cell={formulaCell} />);

    expect(screen.getByText(/Formula Risk \(fx\)/i)).toBeInTheDocument();
  });

  it('renders candidate proposal trigger when inferred_candidate_value is present', () => {
    const candidateCell: CellRecord = {
      ...mockCell,
      inferred_candidate_value: '1350.50',
    };
    const handleOpenProposal = vi.fn();

    render(
      <CellInspector
        isOpen={true}
        onClose={vi.fn()}
        cell={candidateCell}
        onOpenCandidateProposal={handleOpenProposal}
      />
    );

    expect(screen.getByText(/Inferred Candidate Proposal Available/i)).toBeInTheDocument();
    expect(screen.getByText('1350.50')).toBeInTheDocument();

    const reviewBtn = screen.getByRole('button', { name: /Review Evidence & Proposal/i });
    fireEvent.click(reviewBtn);

    expect(handleOpenProposal).toHaveBeenCalledWith(candidateCell);
  });
});
