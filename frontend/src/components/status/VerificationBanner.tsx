import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  FileSearch,
  XCircle,
} from 'lucide-react';
import { Badge } from '../common';
import { VerbatimDisclaimer } from './VerbatimDisclaimer';
import type {
  VerificationStatus,
  JobExecutionState,
} from '../../types/domain';
import {
  REASON_NO_TABLES_FOUND,
  REASON_OCR_REQUIRED_FOR_SCANNED,
  REASON_DEFERRED_REGIONS_REMAIN,
  REASON_SOURCE_ARITHMETIC_DISCREPANCY,
  REASON_ARITHMETIC_SCOPE_AMBIGUOUS,
  REASON_STITCH_REVIEW_REQUIRED,
  REASON_STRUCTURAL_CHECKS_FAILED,
  REASON_EXECUTION_FAILED,
} from '../../types/domain';
import './status.css';

export interface VerificationBannerProps {
  executionState: JobExecutionState;
  verificationStatus: VerificationStatus;
  reasonCodes: string[];
  filename?: string;
  tableCount?: number;
}

const REASON_LABELS: Record<string, { label: string; variant: 'warning' | 'discrepancy' | 'deferred' | 'neutral' }> = {
  [REASON_NO_TABLES_FOUND]: {
    label: 'No Tabular Geometry Detected',
    variant: 'neutral',
  },
  [REASON_OCR_REQUIRED_FOR_SCANNED]: {
    label: 'Scanned Content Requires OCR',
    variant: 'deferred',
  },
  [REASON_DEFERRED_REGIONS_REMAIN]: {
    label: 'Unprocessed Raster Regions',
    variant: 'deferred',
  },
  [REASON_SOURCE_ARITHMETIC_DISCREPANCY]: {
    label: 'Source Arithmetic Discrepancy',
    variant: 'discrepancy',
  },
  [REASON_ARITHMETIC_SCOPE_AMBIGUOUS]: {
    label: 'Ambiguous Arithmetic Scope',
    variant: 'warning',
  },
  [REASON_STITCH_REVIEW_REQUIRED]: {
    label: 'Multipage Stitch Review Required',
    variant: 'warning',
  },
  [REASON_STRUCTURAL_CHECKS_FAILED]: {
    label: 'Structural Integrity Checks Failed',
    variant: 'discrepancy',
  },
  [REASON_EXECUTION_FAILED]: {
    label: 'Pipeline Execution Aborted',
    variant: 'discrepancy',
  },
};

export const VerificationBanner: React.FC<VerificationBannerProps> = ({
  executionState,
  verificationStatus,
  reasonCodes,
  filename,
  tableCount = 0,
}) => {
  // Dimension 1: Operational Job Execution Failure
  if (executionState === 'FAILED') {
    return (
      <div
        className="ds-status-banner ds-status-banner-failed"
        role="alert"
        data-testid="banner-execution-failed"
      >
        <div className="ds-status-header">
          <div className="ds-status-main">
            <XCircle size={22} className="ds-status-icon" aria-hidden="true" />
            <div className="ds-status-content">
              <h3 className="ds-status-title">Pipeline Execution Aborted</h3>
              <p className="ds-status-description">
                The document pipeline encountered an unrecoverable operational barrier while processing{' '}
                {filename ? <strong>{filename}</strong> : 'the document'}.
              </p>
              {reasonCodes.length > 0 && (
                <div className="ds-reason-badges">
                  {reasonCodes.map((code) => (
                    <Badge key={code} variant="discrepancy" size="sm">
                      {REASON_LABELS[code]?.label || code}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
          <Badge variant="discrepancy">Job Failed</Badge>
        </div>
      </div>
    );
  }

  // Dimension 2: Completed Job, but Zero Tables Found (Neutral Informative Result)
  const isZeroTables =
    reasonCodes.includes(REASON_NO_TABLES_FOUND) ||
    (tableCount === 0 && verificationStatus === 'FAILED');

  if (isZeroTables) {
    return (
      <div
        className="ds-status-banner ds-status-banner-zero-tables"
        role="status"
        data-testid="banner-zero-tables"
      >
        <div className="ds-status-header">
          <div className="ds-status-main">
            <FileSearch size={22} className="ds-status-icon" aria-hidden="true" />
            <div className="ds-status-content">
              <h3 className="ds-status-title">0 Tables Detected</h3>
              <p className="ds-status-description">
                Document was fully inspected with confirmed absence of tabular geometry across all digital pages.
              </p>
            </div>
          </div>
          <Badge variant="neutral">Confirmed Absent</Badge>
        </div>
      </div>
    );
  }

  // Dimension 3: Review Required
  if (verificationStatus === 'REVIEW_REQUIRED') {
    return (
      <div
        className="ds-status-banner ds-status-banner-review"
        role="region"
        aria-label="Verification Review Required"
        data-testid="banner-review-required"
      >
        <div className="ds-status-header">
          <div className="ds-status-main">
            <AlertTriangle size={22} className="ds-status-icon" aria-hidden="true" />
            <div className="ds-status-content">
              <h3 className="ds-status-title">Review Required: Diagnostic Flags Present</h3>
              <p className="ds-status-description">
                Extraction completed with findings that require human editorial review prior to downstream usage.
              </p>
              {reasonCodes.length > 0 && (
                <div className="ds-reason-badges">
                  {reasonCodes.map((code) => {
                    const cfg = REASON_LABELS[code] || { label: code, variant: 'warning' };
                    return (
                      <Badge key={code} variant={cfg.variant} size="sm">
                        {cfg.label}
                      </Badge>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <Badge variant="warning">Review Required</Badge>
        </div>
      </div>
    );
  }

  // Dimension 4: Verified with Warnings
  if (verificationStatus === 'VERIFIED_WITH_WARNINGS') {
    return (
      <div
        className="ds-status-banner ds-status-banner-warning"
        role="region"
        aria-label="Verified with Warnings"
        data-testid="banner-verified-with-warnings"
      >
        <div className="ds-status-header">
          <div className="ds-status-main">
            <AlertTriangle size={22} className="ds-status-icon" aria-hidden="true" />
            <div className="ds-status-content">
              <h3 className="ds-status-title">Verified With Warnings</h3>
              <p className="ds-status-description">
                Structural integrity validated. Non-blocking caveats (e.g. arithmetic check not applicable, or evidence-gated corrections) were logged.
              </p>
              {reasonCodes.length > 0 && (
                <div className="ds-reason-badges">
                  {reasonCodes.map((code) => (
                    <Badge key={code} variant="warning" size="sm">
                      {REASON_LABELS[code]?.label || code}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
          <Badge variant="warning">Verified (Warnings)</Badge>
        </div>
        <VerbatimDisclaimer />
      </div>
    );
  }

  // Dimension 5: Fully Verified
  if (verificationStatus === 'VERIFIED') {
    return (
      <div
        className="ds-status-banner ds-status-banner-verified"
        role="region"
        aria-label="Verified Document"
        data-testid="banner-verified"
      >
        <div className="ds-status-header">
          <div className="ds-status-main">
            <CheckCircle2 size={22} className="ds-status-icon" aria-hidden="true" />
            <div className="ds-status-content">
              <h3 className="ds-status-title">Verified: Structural Integrity & Arithmetic Validated</h3>
              <p className="ds-status-description">
                100% digital page inspection passed. Zero deferred raster regions, table structure intact, and mathematical consistency confirmed.
              </p>
            </div>
          </div>
          <Badge variant="verified">Verified</Badge>
        </div>
        <VerbatimDisclaimer />
      </div>
    );
  }

  // Fallback: Generic Failed Status
  return (
    <div
      className="ds-status-banner ds-status-banner-failed"
      role="alert"
      data-testid="banner-failed-generic"
    >
      <div className="ds-status-header">
        <div className="ds-status-main">
          <AlertOctagon size={22} className="ds-status-icon" aria-hidden="true" />
          <div className="ds-status-content">
            <h3 className="ds-status-title">Quality Verification Failed</h3>
            <p className="ds-status-description">
              The document quality gate rejected verification due to structural or validation discrepancies.
            </p>
            {reasonCodes.length > 0 && (
              <div className="ds-reason-badges">
                {reasonCodes.map((code) => (
                  <Badge key={code} variant="discrepancy" size="sm">
                    {REASON_LABELS[code]?.label || code}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <Badge variant="discrepancy">Failed</Badge>
      </div>
    </div>
  );
};
