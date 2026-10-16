import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentUpload } from '../upload';
import { apiClient, MAX_FILE_SIZE_BYTES } from '../../api/client';
import type { DocumentEvaluationReport } from '../../types/domain';

describe('DocumentUpload Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders initial dropzone with 25 MiB and PDF-only limits', () => {
    render(<DocumentUpload onExtractionSuccess={vi.fn()} />);

    expect(
      screen.getByText(/Upload PDF for Deterministic Extraction/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Max Size: 50 MiB/i)).toBeInTheDocument();
    expect(screen.getByText(/Format: PDF & Document Images/i)).toBeInTheDocument();
  });

  it('rejects non-PDF files immediately with client validation error', () => {
    render(<DocumentUpload onExtractionSuccess={vi.fn()} />);

    const fileInput = screen.getByTestId('file-input');
    const txtFile = new File(['hello world'], 'report.txt', { type: 'text/plain' });

    fireEvent.change(fileInput, { target: { files: [txtFile] } });

    expect(
      screen.getByText(/Only PDF documents \(\.pdf\) are supported/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Select Another Document/i })
    ).toBeInTheDocument();
  });

  it('rejects files exceeding 25 MiB ceiling immediately without network call', () => {
    const extractSpy = vi.spyOn(apiClient, 'extractDocument');
    render(<DocumentUpload onExtractionSuccess={vi.fn()} />);

    const oversizedFile = new File(['x'.repeat(100)], 'large.pdf', {
      type: 'application/pdf',
    });
    Object.defineProperty(oversizedFile, 'size', {
      value: MAX_FILE_SIZE_BYTES + 500,
    });

    const fileInput = screen.getByTestId('file-input');
    fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

    expect(
      screen.getByText(/exceeds the 50 MiB operational limit/i)
    ).toBeInTheDocument();
    expect(extractSpy).not.toHaveBeenCalled();
  });

  it('shows selected file details and triggers extraction upon Run button click', async () => {
    const mockReport: DocumentEvaluationReport = {
      job_id: 'job_456',
      source_filename: 'balance_sheet.pdf',
      execution_state: 'COMPLETED',
      verification_status: 'VERIFIED',
      status_reason_codes: [],
      limitation_disclaimers: [],
      page_profiles: [],
      page_results: [],
      canonical_tables: [],
      stitch_events: [],
      validation_issues: [],
      correction_records: [],
      peak_python_heap_bytes: 1048576,
    };

    const extractSpy = vi
      .spyOn(apiClient, 'extractDocument')
      .mockResolvedValueOnce(mockReport);
    const handleSuccess = vi.fn();

    render(<DocumentUpload onExtractionSuccess={handleSuccess} />);

    const validFile = new File(['%PDF-1.4 content'], 'balance_sheet.pdf', {
      type: 'application/pdf',
    });

    const fileInput = screen.getByTestId('file-input');
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    expect(screen.getByText('balance_sheet.pdf')).toBeInTheDocument();
    const runBtn = screen.getByRole('button', { name: /Run Extraction/i });
    expect(runBtn).toBeInTheDocument();

    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(extractSpy).toHaveBeenCalledWith(validFile, expect.any(AbortSignal));
      expect(handleSuccess).toHaveBeenCalledWith(mockReport);
    });
  });

  it('handles extraction failure and displays error barrier callout', async () => {
    vi.spyOn(apiClient, 'extractDocument').mockRejectedValueOnce({
      detail: 'Corrupt PDF signature at byte offset 0.',
      status_code: 422,
    });
    const handleError = vi.fn();

    render(
      <DocumentUpload
        onExtractionSuccess={vi.fn()}
        onExtractionError={handleError}
      />
    );

    const validFile = new File(['corrupt data'], 'corrupt.pdf', {
      type: 'application/pdf',
    });

    const fileInput = screen.getByTestId('file-input');
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    const runBtn = screen.getByRole('button', { name: /Run Extraction/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Corrupt PDF signature at byte offset 0/i)
      ).toBeInTheDocument();
      expect(handleError).toHaveBeenCalled();
    });
  });
});
