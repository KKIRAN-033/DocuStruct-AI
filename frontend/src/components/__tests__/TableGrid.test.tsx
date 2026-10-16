import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TableGrid } from '../table';
import type { CanonicalTable, CellRecord, DataType } from '../../types/domain';

const createMockCell = (
  row_idx: number,
  col_idx: number,
  raw_value: string,
  accepted_value: string,
  formula_risk: boolean = false,
  dataType: DataType = 'STRING'
): CellRecord => ({
  table_id: 'tbl_1',
  row_idx,
  col_idx,
  source_page: 1,
  bbox: {
    x0: 10,
    y0: 20,
    x1: 100,
    y1: 40,
    page_width: 612,
    page_height: 792,
    coord_exact: true,
    norm_x0: 0.016,
    norm_x1: 0.163,
    norm_y0: 0.025,
    norm_y1: 0.05,
  },
  extraction_method: 'DIGITAL_RULING_LINES',
  ocr_confidence: null,
  raw_value,
  normalized_value: accepted_value,
  numeric_decimal: dataType === 'DECIMAL' ? accepted_value : null,
  accepted_value,
  inferred_candidate_value: null,
  data_type: dataType,
  quality_status: 'EXTRACTED_AS_IS',
  formula_risk_detected: formula_risk,
  notes: [],
});

describe('TableGrid Component', () => {
  const mockTable: CanonicalTable = {
    table_id: 'tbl_1',
    title: 'Financial Balance Sheet',
    source_pages: [1],
    page_bbox: null,
    original_headers: ['Account', 'Q1 Amount', 'Q2 Amount'],
    normalized_headers: ['Account Name', 'Q1 Revenue', 'Q2 Revenue'],
    header_row_count: 1,
    column_types: ['STRING', 'DECIMAL', 'DECIMAL'],
    column_semantic_roles: [],
    rows: [
      [
        createMockCell(0, 0, 'Consulting Revenue', 'Consulting Revenue', false, 'STRING'),
        createMockCell(0, 1, '12000.00', '12000.00', false, 'DECIMAL'),
        createMockCell(0, 2, '15000.00', '15000.00', false, 'DECIMAL'),
      ],
      [
        createMockCell(1, 0, '=SUM(A1:A2)', '=SUM(A1:A2)', true, 'STRING'),
        createMockCell(1, 1, '8000.00', '8000.00', false, 'DECIMAL'),
        createMockCell(1, 2, '9000.00', '9000.00', false, 'DECIMAL'),
      ],
      [
        createMockCell(2, 0, 'Total Revenue', 'Total Revenue', false, 'STRING'),
        createMockCell(2, 1, '20000.00', '20000.00', false, 'DECIMAL'),
        createMockCell(2, 2, '24000.00', '24000.00', false, 'DECIMAL'),
      ],
    ],
    extraction_method: 'DIGITAL_RULING_LINES',
    stitch_events: [],
    validation_issues: [],
    correction_records: [],
    structural_checks_passed: true,
    math_validation_outcome: 'PASSED',
    verification_status: 'VERIFIED',
  };

  it('renders headers, column types, and data cells', () => {
    render(<TableGrid tables={[mockTable]} />);

    expect(screen.getByText('Account Name')).toBeInTheDocument();
    expect(screen.getByText('Q1 Revenue')).toBeInTheDocument();
    expect(screen.getByText('Consulting Revenue')).toBeInTheDocument();
    expect(screen.getByText('12000.00')).toBeInTheDocument();
  });

  it('highlights summary rows with .ds-row-summary class', () => {
    render(<TableGrid tables={[mockTable]} />);

    const totalRow = screen.getByTestId('table-row-2');
    expect(totalRow).toHaveClass('ds-row-summary');
  });

  it('renders formula risk badge (fx) without mutating cell string', () => {
    render(<TableGrid tables={[mockTable]} />);

    const fxBadge = screen.getByText('fx');
    expect(fxBadge).toBeInTheDocument();

    // The text "=SUM(A1:A2)" must remain clean and unaltered (no prepended apostrophes)
    expect(screen.getByText('=SUM(A1:A2)')).toBeInTheDocument();
  });

  it('invokes onSelectCell when cell is clicked or triggered by Enter key', () => {
    const handleSelect = vi.fn();
    render(<TableGrid tables={[mockTable]} onSelectCell={handleSelect} />);

    const cellEl = screen.getByText('Consulting Revenue');
    fireEvent.click(cellEl);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith(mockTable.rows[0][0]);

    const numCell = screen.getByText('12000.00').closest('td')!;
    fireEvent.keyDown(numCell, { key: 'Enter' });
    expect(handleSelect).toHaveBeenCalledWith(mockTable.rows[0][1]);
  });

  it('renders tabs when multiple canonical tables are present', () => {
    const table2: CanonicalTable = {
      ...mockTable,
      table_id: 'tbl_2',
      title: 'Tax Schedule',
      source_pages: [2],
    };

    render(<TableGrid tables={[mockTable, table2]} />);

    expect(screen.getByText(/Table 1: Page 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Table 2: Page 2/i)).toBeInTheDocument();

    // Click table 2 tab
    fireEvent.click(screen.getByText(/Table 2: Page 2/i));
    expect(screen.getByText(/Tax Schedule/i)).toBeInTheDocument();
  });

  it('allows adding a new row via Add Row modal', () => {
    const handleAddRow = vi.fn();
    render(<TableGrid tables={[mockTable]} onAddRow={handleAddRow} />);

    // Click "+ Add Row" button
    const addRowBtn = screen.getByTestId('add-row-button');
    fireEvent.click(addRowBtn);

    // Modal should be open with input for each column
    expect(screen.getByText('Add New Row')).toBeInTheDocument();
    const input0 = screen.getByTestId('row-modal-input-0');
    const input1 = screen.getByTestId('row-modal-input-1');
    const input2 = screen.getByTestId('row-modal-input-2');

    fireEvent.change(input0, { target: { value: 'Software License' } });
    fireEvent.change(input1, { target: { value: '5000.00' } });
    fireEvent.change(input2, { target: { value: '6000.00' } });

    // Submit modal
    const submitBtn = screen.getByTestId('submit-row-modal');
    fireEvent.click(submitBtn);

    expect(handleAddRow).toHaveBeenCalledTimes(1);
    expect(handleAddRow).toHaveBeenCalledWith('tbl_1', ['Software License', '5000.00', '6000.00']);
  });

  it('allows editing an existing row via Edit Row modal', () => {
    const handleEditRow = vi.fn();
    render(<TableGrid tables={[mockTable]} onEditRow={handleEditRow} />);

    // Click edit row button on row 0
    const editBtn = screen.getByTestId('edit-row-0');
    fireEvent.click(editBtn);

    // Modal opens with pre-filled row values
    expect(screen.getByText('Edit Row #1')).toBeInTheDocument();
    const input0 = screen.getByTestId('row-modal-input-0') as HTMLInputElement;
    expect(input0.value).toBe('Consulting Revenue');

    fireEvent.change(input0, { target: { value: 'Advisory Revenue' } });

    const submitBtn = screen.getByTestId('submit-row-modal');
    fireEvent.click(submitBtn);

    expect(handleEditRow).toHaveBeenCalledTimes(1);
    expect(handleEditRow).toHaveBeenCalledWith('tbl_1', 0, ['Advisory Revenue', '12000.00', '15000.00']);
  });

  it('allows inline cell editing via double-click and Enter key', () => {
    const handleUpdateCell = vi.fn();
    render(<TableGrid tables={[mockTable]} onUpdateCell={handleUpdateCell} />);

    const cell = screen.getByText('Consulting Revenue').closest('td')!;
    fireEvent.doubleClick(cell);

    // Inline edit input should appear
    const inlineInput = screen.getByTestId('inline-edit-input-0-0') as HTMLInputElement;
    expect(inlineInput).toBeInTheDocument();
    expect(inlineInput.value).toBe('Consulting Revenue');

    fireEvent.change(inlineInput, { target: { value: 'Updated Consulting' } });
    fireEvent.keyDown(inlineInput, { key: 'Enter' });

    expect(handleUpdateCell).toHaveBeenCalledTimes(1);
    expect(handleUpdateCell).toHaveBeenCalledWith('tbl_1', 0, 0, 'Updated Consulting');
  });

  it('allows deleting a row via row delete action', () => {
    const handleDeleteRow = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<TableGrid tables={[mockTable]} onDeleteRow={handleDeleteRow} />);

    const deleteBtn = screen.getByTestId('delete-row-0');
    fireEvent.click(deleteBtn);

    expect(handleDeleteRow).toHaveBeenCalledTimes(1);
    expect(handleDeleteRow).toHaveBeenCalledWith('tbl_1', 0);
  });
});

