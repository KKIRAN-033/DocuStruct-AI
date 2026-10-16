import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VerificationBanner, VerbatimDisclaimer } from '../status';
import {
  MANDATORY_VERBATIM_DISCLAIMER,
  REASON_NO_TABLES_FOUND,
  REASON_OCR_REQUIRED_FOR_SCANNED,
  REASON_SOURCE_ARITHMETIC_DISCREPANCY,
} from '../../types/domain';

describe('VerificationBanner & VerbatimDisclaimer', () => {
  it('renders exact mandatory verbatim disclaimer text without omission or alteration', () => {
    render(<VerbatimDisclaimer />);

    const disclaimerEl = screen.getByTestId('verbatim-disclaimer');
    expect(disclaimerEl).toBeInTheDocument();
    expect(disclaimerEl).toHaveTextContent(MANDATORY_VERBATIM_DISCLAIMER);
    expect(disclaimerEl).toHaveTextContent(
      'Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text.'
    );
  });

  it('renders high-priority alert for JobExecutionState.FAILED', () => {
    render(
      <VerificationBanner
        executionState="FAILED"
        verificationStatus="FAILED"
        reasonCodes={['CORRUPT_PDF']}
        filename="corrupted.pdf"
      />
    );

    expect(screen.getByTestId('banner-execution-failed')).toBeInTheDocument();
    expect(screen.getByText(/Pipeline Execution Aborted/i)).toBeInTheDocument();
    expect(screen.getByText('corrupted.pdf')).toBeInTheDocument();
  });

  it('renders neutral zero-tables banner for completed job with NO_TABLES_FOUND', () => {
    render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="FAILED"
        reasonCodes={[REASON_NO_TABLES_FOUND]}
        tableCount={0}
      />
    );

    expect(screen.getByTestId('banner-zero-tables')).toBeInTheDocument();
    expect(screen.getByText(/0 Tables Detected/i)).toBeInTheDocument();
    expect(
      screen.getByText(/confirmed absence of tabular geometry across all digital pages/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Confirmed Absent/i)).toBeInTheDocument();
  });

  it('renders review banner with diagnostic badges for REVIEW_REQUIRED', () => {
    render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="REVIEW_REQUIRED"
        reasonCodes={[
          REASON_OCR_REQUIRED_FOR_SCANNED,
          REASON_SOURCE_ARITHMETIC_DISCREPANCY,
        ]}
        tableCount={1}
      />
    );

    expect(screen.getByTestId('banner-review-required')).toBeInTheDocument();
    expect(screen.getByText(/Review Required: Diagnostic Flags Present/i)).toBeInTheDocument();
    expect(screen.getByText(/Scanned Content Requires OCR/i)).toBeInTheDocument();
    expect(screen.getByText(/Source Arithmetic Discrepancy/i)).toBeInTheDocument();
  });

  it('renders verified banner with verbatim disclaimer for VERIFIED status', () => {
    render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="VERIFIED"
        reasonCodes={[]}
        tableCount={1}
      />
    );

    expect(screen.getByTestId('banner-verified')).toBeInTheDocument();
    expect(
      screen.getByText(/Verified: Structural Integrity & Arithmetic Validated/i)
    ).toBeInTheDocument();
    expect(screen.getByTestId('verbatim-disclaimer')).toBeInTheDocument();
  });

  it('renders verified-with-warnings banner and disclaimer for VERIFIED_WITH_WARNINGS', () => {
    render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="VERIFIED_WITH_WARNINGS"
        reasonCodes={['ARITHMETIC_NOT_APPLICABLE']}
        tableCount={1}
      />
    );

    expect(screen.getByTestId('banner-verified-with-warnings')).toBeInTheDocument();
    expect(screen.getByText(/Verified With Warnings/i)).toBeInTheDocument();
    expect(screen.getByTestId('verbatim-disclaimer')).toBeInTheDocument();
  });
});
