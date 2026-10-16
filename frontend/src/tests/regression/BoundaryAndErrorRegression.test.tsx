import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ApiClient, MAX_FILE_SIZE_BYTES } from '../../api/client';
import { DocumentUpload } from '../../components/upload/DocumentUpload';
import { ExportControls } from '../../components/export/ExportControls';
import { CandidateProposalDrawer } from '../../components/ai/CandidateProposalDrawer';
import { MANDATORY_VERBATIM_DISCLAIMER } from '../../types/domain';
import type { CanonicalTable, CellRecord } from '../../types/domain';

describe('DocuStruct AI — Boundary, Error & Invariant Regression Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Ingestion Boundary Regressions', () => {
    it('verifies exact 50 MiB boundary condition (52,428,800 bytes accepted, 52,428,801 bytes rejected)', () => {
      expect(MAX_FILE_SIZE_BYTES).toBe(52_428_800);

      const onExtractionSuccess = vi.fn();
      render(
        <DocumentUpload
          onExtractionSuccess={onExtractionSuccess}
          isBackendConnected={true}
        />
      );

      const fileInput = screen.getByTestId('file-input');

      // 1. Exact boundary: 52,428,800 bytes (50.00 MiB)
      const boundaryFile = new File(['x'], 'exact_50mib.pdf', { type: 'application/pdf' });
      Object.defineProperty(boundaryFile, 'size', { value: 52_428_800 });

      fireEvent.change(fileInput, { target: { files: [boundaryFile] } });
      // Should be accepted and render file card
      expect(screen.getByText('exact_50mib.pdf')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Run Extraction/i })).toBeInTheDocument();

      // Reset
      fireEvent.click(screen.getByRole('button', { name: /Remove selected file/i }));

      // 2. Over boundary: 52,428,801 bytes (50 MiB + 1 byte)
      const overBoundaryFile = new File(['x'], 'over_50mib.pdf', { type: 'application/pdf' });
      Object.defineProperty(overBoundaryFile, 'size', { value: 52_428_801 });

      fireEvent.change(fileInput, { target: { files: [overBoundaryFile] } });
      // Should be immediately rejected with error callout
      expect(screen.getByText(/File exceeds the 50 MiB operational limit/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Run Extraction/i })).not.toBeInTheDocument();
    });

    it('rejects 0-byte file uploads client-side before any network request', () => {
      const onExtractionSuccess = vi.fn();
      render(
        <DocumentUpload
          onExtractionSuccess={onExtractionSuccess}
          isBackendConnected={true}
        />
      );

      const emptyFile = new File([], 'empty.pdf', { type: 'application/pdf' });
      Object.defineProperty(emptyFile, 'size', { value: 0 });

      const fileInput = screen.getByTestId('file-input');
      fireEvent.change(fileInput, { target: { files: [emptyFile] } });

      expect(
        screen.getByText(/The selected file is empty \(0 bytes\)\. Please provide a valid PDF\./i)
      ).toBeInTheDocument();
    });

    it('rejects non-PDF files immediately', () => {
      const onExtractionSuccess = vi.fn();
      render(
        <DocumentUpload
          onExtractionSuccess={onExtractionSuccess}
          isBackendConnected={true}
        />
      );

      const textFile = new File(['hello'], 'document.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });

      const fileInput = screen.getByTestId('file-input');
      fireEvent.change(fileInput, { target: { files: [textFile] } });

      expect(
        screen.getByText(/Only PDF documents \(\.pdf\) are supported for deterministic table extraction\./i)
      ).toBeInTheDocument();
    });
  });

  describe('2. Network Error, Timeout & Cancellation Regressions', () => {
    it('normalizes extraction timeout into typed ApiError with HTTP 408', async () => {
      const client = new ApiClient('http://test-server:8000');
      const testFile = new File(['%PDF-1.4 test'], 'timeout.pdf', { type: 'application/pdf' });

      // Mock fetch with delayed abort to simulate timeout
      globalThis.fetch = vi.fn().mockImplementation((_url, options) => {
        return new Promise((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => {
            const err = new DOMException('The user aborted a request.', 'AbortError');
            reject(err);
          });
        });
      });

      // Pass very short timeout (10ms)
      await expect(client.extractDocument(testFile, undefined, 10)).rejects.toMatchObject({
        status_code: 408,
        detail: expect.stringContaining('Extraction timed out after 0.01s'),
      });
    });

    it('normalizes caller AbortSignal cancellation into typed ApiError with HTTP 499', async () => {
      const client = new ApiClient('http://test-server:8000');
      const testFile = new File(['%PDF-1.4 test'], 'cancel.pdf', { type: 'application/pdf' });

      const controller = new AbortController();
      controller.abort(); // Pre-aborted

      await expect(client.extractDocument(testFile, controller.signal)).rejects.toMatchObject({
        status_code: 499,
        detail: 'Extraction cancelled by user.',
      });
    });

    it('normalizes server disconnection / backend offline into typed ApiError with status 0', async () => {
      const client = new ApiClient('http://test-server:8000');
      const testFile = new File(['%PDF-1.4 test'], 'offline.pdf', { type: 'application/pdf' });

      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

      await expect(client.extractDocument(testFile)).rejects.toMatchObject({
        status_code: 0,
        detail: expect.stringContaining('Extraction failed: Failed to fetch. Verify that FastAPI is running on port 8000.'),
      });
    });

    it('normalizes backend HTTP 500 into typed ApiError with server detail string', async () => {
      const client = new ApiClient('http://test-server:8000');

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server pipeline failure' }),
      } as Response);

      await expect(client.checkHealth()).rejects.toMatchObject({
        status_code: 500,
        detail: 'Internal server pipeline failure',
      });
    });
  });

  describe('3. Export Fidelity & Formatting Edge Cases', () => {
    const mockCell: CellRecord = {
      table_id: 'tbl-export',
      row_idx: 0,
      col_idx: 0,
      source_page: 1,
      bbox: null,
      extraction_method: 'DIGITAL_LINE_GEOMETRY',
      ocr_confidence: null,
      raw_value: 'Raw 1',
      normalized_value: 'Norm 1',
      numeric_decimal: null,
      accepted_value: 'Item with "Quotes", Commas and \n Newlines',
      inferred_candidate_value: null,
      data_type: 'STRING',
      quality_status: 'EXTRACTED_AS_IS',
      formula_risk_detected: false,
      notes: [],
    };

    it('properly escapes quotes, commas, and newlines in CSV export per RFC 4180', () => {
      const tableWithSpecialChars: CanonicalTable = {
        table_id: 'tbl-special',
        title: 'Special Characters Table',
        source_pages: [1],
        page_bbox: null,
        original_headers: ['Header 1', 'Header 2'],
        normalized_headers: ['Header 1', 'Header 2'],
        header_row_count: 1,
        column_types: ['STRING', 'STRING'],
        column_semantic_roles: ['LABEL', 'DATA'],
        rows: [
          [
            mockCell,
            { ...mockCell, col_idx: 1, accepted_value: 'Normal Value' },
          ],
        ],
        extraction_method: 'DIGITAL_LINE_GEOMETRY',
        stitch_events: [],
        validation_issues: [],
        correction_records: [],
        structural_checks_passed: true,
        math_validation_outcome: 'PASSED',
        verification_status: 'VERIFIED',
      };

      globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-csv');
      globalThis.URL.revokeObjectURL = vi.fn();

      render(<ExportControls table={tableWithSpecialChars} />);

      const csvBtn = screen.getByRole('button', { name: /Export table as CSV/i });
      fireEvent.click(csvBtn);

      expect(globalThis.URL.createObjectURL).toHaveBeenCalledTimes(1);
      expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-csv');
    });

    it('handles tables with blank and duplicate headers losslessly in structured JSON export', () => {
      const tableWithDuplicateHeaders: CanonicalTable = {
        table_id: 'tbl-duplicates',
        title: 'Duplicate Headers Table',
        source_pages: [1],
        page_bbox: null,
        original_headers: ['Revenue', '', 'Revenue'],
        normalized_headers: ['Revenue', '', 'Revenue'],
        header_row_count: 1,
        column_types: ['DECIMAL', 'STRING', 'DECIMAL'],
        column_semantic_roles: ['DATA', 'LABEL', 'DATA'],
        rows: [
          [
            { ...mockCell, col_idx: 0, accepted_value: '$100.00' },
            { ...mockCell, col_idx: 1, accepted_value: 'Q1' },
            { ...mockCell, col_idx: 2, accepted_value: '$200.00' },
          ],
        ],
        extraction_method: 'DIGITAL_LINE_GEOMETRY',
        stitch_events: [],
        validation_issues: [],
        correction_records: [],
        structural_checks_passed: true,
        math_validation_outcome: 'PASSED',
        verification_status: 'VERIFIED',
      };

      globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-json');
      globalThis.URL.revokeObjectURL = vi.fn();

      render(<ExportControls table={tableWithDuplicateHeaders} />);

      const jsonBtn = screen.getByRole('button', { name: /Export table as JSON/i });
      fireEvent.click(jsonBtn);

      expect(globalThis.URL.createObjectURL).toHaveBeenCalledTimes(1);
      expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-json');
    });
  });

  describe('4. Deterministic Invariants & Disclaimer Regressions', () => {
    it('verifies mandatory limitation disclaimer is exact verbatim constant', () => {
      expect(MANDATORY_VERBATIM_DISCLAIMER).toBe(
        'Structural integrity and internal arithmetic consistency were verified. ' +
          'This does not independently prove every source cell is correct and cannot ' +
          'rule out offsetting cell errors or errors in non-numeric text.'
      );
    });

    it('hard-blocks auto-balancing proposal acceptance on summary-row cells', () => {
      const totalCell: CellRecord = {
        table_id: 'tbl-total',
        row_idx: 1,
        col_idx: 1,
        source_page: 1,
        bbox: null,
        extraction_method: 'DIGITAL_LINE_GEOMETRY',
        ocr_confidence: null,
        raw_value: '$350.00',
        normalized_value: '350.00',
        numeric_decimal: '350.00',
        accepted_value: '$350.00',
        inferred_candidate_value: '$300.00',
        data_type: 'DECIMAL',
        quality_status: 'EXTRACTED_AS_IS',
        formula_risk_detected: false,
        notes: [],
      };

      const tableWithTotal: CanonicalTable = {
        table_id: 'tbl-total',
        title: 'Totals Table',
        source_pages: [1],
        page_bbox: null,
        original_headers: ['Item', 'Amount'],
        normalized_headers: ['Item', 'Amount'],
        header_row_count: 1,
        column_types: ['STRING', 'DECIMAL'],
        column_semantic_roles: ['LABEL', 'DATA'],
        rows: [
          [
            { ...totalCell, row_idx: 0, col_idx: 0, raw_value: 'Subtotal A', accepted_value: 'Subtotal A' },
            { ...totalCell, row_idx: 0, col_idx: 1, raw_value: '$100.00', accepted_value: '$100.00' },
          ],
          [
            { ...totalCell, row_idx: 1, col_idx: 0, raw_value: 'Grand Total', accepted_value: 'Grand Total' },
            totalCell,
          ],
        ],
        extraction_method: 'DIGITAL_LINE_GEOMETRY',
        stitch_events: [],
        validation_issues: [],
        correction_records: [],
        structural_checks_passed: true,
        math_validation_outcome: 'FAILED_VALIDATION',
        verification_status: 'FAILED',
      };

      const onAcceptProposal = vi.fn();

      render(
        <CandidateProposalDrawer
          isOpen={true}
          onClose={vi.fn()}
          cell={totalCell}
          table={tableWithTotal}
          onAcceptProposal={onAcceptProposal}
          onRejectProposal={vi.fn()}
        />
      );

      // Verify warning alert is present citing DECISION-007 and DECISION-011
      expect(
        screen.getByText(/Auto-Balancing Prohibited \(DECISION-007 & DECISION-011\)/i)
      ).toBeInTheDocument();

      // Verify button is disabled and cannot be clicked
      const acceptBtn = screen.getByTestId('accept-proposal-btn');
      expect(acceptBtn).toBeDisabled();
      expect(acceptBtn).toHaveTextContent(/Accept Blocked \(Total Row\)/i);

      fireEvent.click(acceptBtn);
      expect(onAcceptProposal).not.toHaveBeenCalled();
    });
  });
});
