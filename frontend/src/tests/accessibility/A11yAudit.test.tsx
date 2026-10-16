import { describe, it, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { expectNoA11yViolations } from '../../test/a11y';
import { DocumentUpload } from '../../components/upload/DocumentUpload';
import { VerificationBanner } from '../../components/status/VerificationBanner';
import { VerbatimDisclaimer } from '../../components/status/VerbatimDisclaimer';
import { TableGrid } from '../../components/table/TableGrid';
import { CellInspector } from '../../components/table/CellInspector';
import { CandidateProposalDrawer } from '../../components/ai/CandidateProposalDrawer';
import { DiscrepancyAdjudication } from '../../components/ai/DiscrepancyAdjudication';
import { PageProfiles } from '../../components/audit/PageProfiles';
import { StitchAudit } from '../../components/audit/StitchAudit';
import { ModelRegistryDrawer } from '../../components/layout/ModelRegistryDrawer';
import { Header } from '../../components/layout/Header';
import type {
  CanonicalTable,
  CellRecord,
  ValidationIssue,
  PageProfile,
  StitchAuditEvent,
} from '../../types/domain';

// Mock API client for subcomponents
vi.mock('../../api/client', () => ({
  apiClient: {
    getModelsStatus: vi.fn().mockResolvedValue({
      models: [],
      providers: {},
      timestamp: '2026-10-15T12:00:00Z',
    }),
  },
  MAX_FILE_SIZE_BYTES: 52_428_800,
}));

describe('Automated WCAG Accessibility Audit (axe-core)', () => {
  const mockCell: CellRecord = {
    table_id: 'table-1',
    row_idx: 0,
    col_idx: 1,
    source_page: 1,
    bbox: {
      x0: 100,
      y0: 200,
      x1: 180,
      y1: 220,
      page_width: 612,
      page_height: 792,
      coord_exact: true,
      norm_x0: 0.16,
      norm_x1: 0.29,
      norm_y0: 0.25,
      norm_y1: 0.28,
    },
    extraction_method: 'DIGITAL_LINE_GEOMETRY',
    ocr_confidence: null,
    raw_value: '$1,250.00',
    normalized_value: '1250.00',
    numeric_decimal: '1250.00',
    accepted_value: '$1,250.00',
    inferred_candidate_value: null,
    data_type: 'DECIMAL',
    quality_status: 'EXTRACTED_AS_IS',
    formula_risk_detected: false,
    notes: [],
  };

  const mockTotalCell: CellRecord = {
    ...mockCell,
    row_idx: 2,
    raw_value: '$3,750.00',
    accepted_value: '$3,750.00',
    inferred_candidate_value: '$3,500.00',
  };

  const mockTable: CanonicalTable = {
    table_id: 'table-1',
    title: 'Financial Q3 Summary',
    source_pages: [1],
    page_bbox: null,
    original_headers: ['Category', 'Amount'],
    normalized_headers: ['Category', 'Amount'],
    header_row_count: 1,
    column_types: ['STRING', 'DECIMAL'],
    column_semantic_roles: ['LABEL', 'DATA'],
    rows: [
      [
        { ...mockCell, col_idx: 0, raw_value: 'Product A', accepted_value: 'Product A', data_type: 'STRING' },
        mockCell,
      ],
      [
        { ...mockCell, row_idx: 1, col_idx: 0, raw_value: 'Product B', accepted_value: 'Product B', data_type: 'STRING' },
        { ...mockCell, row_idx: 1, col_idx: 1, raw_value: '$2,500.00', accepted_value: '$2,500.00' },
      ],
      [
        { ...mockCell, row_idx: 2, col_idx: 0, raw_value: 'Total', accepted_value: 'Total', data_type: 'STRING' },
        mockTotalCell,
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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes WCAG audit for DocumentUpload in IDLE state', async () => {
    const { container } = render(
      <DocumentUpload onExtractionSuccess={vi.fn()} isBackendConnected={true} />
    );
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for VerbatimDisclaimer', async () => {
    const { container } = render(<VerbatimDisclaimer />);
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for VerificationBanner across all verification statuses', async () => {
    // 1. VERIFIED
    const { container: c1 } = render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="VERIFIED"
        reasonCodes={[]}
        tableCount={1}
      />
    );
    await expectNoA11yViolations(c1);

    // 2. VERIFIED_WITH_WARNINGS
    const { container: c2 } = render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="VERIFIED_WITH_WARNINGS"
        reasonCodes={['ARITHMETIC_CHECKS_NOT_APPLICABLE']}
        tableCount={1}
      />
    );
    await expectNoA11yViolations(c2);

    // 3. REVIEW_REQUIRED
    const { container: c3 } = render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="REVIEW_REQUIRED"
        reasonCodes={['SOURCE_ARITHMETIC_DISCREPANCY']}
        tableCount={1}
      />
    );
    await expectNoA11yViolations(c3);

    // 4. Zero Tables Found
    const { container: c4 } = render(
      <VerificationBanner
        executionState="COMPLETED"
        verificationStatus="FAILED"
        reasonCodes={['NO_TABLES_FOUND']}
        tableCount={0}
      />
    );
    await expectNoA11yViolations(c4);

    // 5. Job Execution Failed
    const { container: c5 } = render(
      <VerificationBanner
        executionState="FAILED"
        verificationStatus="FAILED"
        reasonCodes={['CORRUPT_PDF']}
        tableCount={0}
      />
    );
    await expectNoA11yViolations(c5);
  });

  it('passes WCAG audit for TableGrid with summary rows and formula risk', async () => {
    const tableWithFx: CanonicalTable = {
      ...mockTable,
      table_id: 'table-2',
      rows: [
        [
          { ...mockCell, table_id: 'table-2', raw_value: '=SUM(A1:A2)', formula_risk_detected: true },
          { ...mockCell, table_id: 'table-2', col_idx: 1 },
        ],
      ],
    };

    const { container } = render(
      <TableGrid tables={[mockTable, tableWithFx]} onSelectCell={vi.fn()} />
    );
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for CellInspector drawer when open', async () => {
    const { baseElement } = render(
      <CellInspector isOpen={true} onClose={vi.fn()} cell={mockCell} />
    );
    await expectNoA11yViolations(baseElement);
  });

  it('passes WCAG audit for CandidateProposalDrawer with auto-balance prohibition', async () => {
    const { baseElement } = render(
      <CandidateProposalDrawer
        isOpen={true}
        onClose={vi.fn()}
        cell={mockTotalCell}
        table={mockTable}
        onAcceptProposal={vi.fn()}
        onRejectProposal={vi.fn()}
      />
    );
    await expectNoA11yViolations(baseElement);
  });

  it('passes WCAG audit for DiscrepancyAdjudication with issues', async () => {
    const issues: ValidationIssue[] = [
      {
        issue_id: 'iss-1',
        table_id: 'table-1',
        row_idx: 2,
        col_idx: 1,
        source_page: 1,
        issue_code: 'SOURCE_ARITHMETIC_DISCREPANCY',
        severity: 'HIGH',
        description: 'Printed total $3,750.00 diverges from calculated sum $3,500.00 (diff: +$250.00)',
        actual_value: '$3,750.00',
        expected_value: '$3,500.00',
        resolved: false,
      },
    ];

    const { container } = render(
      <DiscrepancyAdjudication issues={issues} onToggleResolve={vi.fn()} />
    );
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for PageProfiles diagnostic table', async () => {
    const profiles: PageProfile[] = [
      {
        page_number: 1,
        page_type: 'DIGITAL',
        processing_status: 'EXTRACTED',
        printable_char_count: 1420,
        garbled_char_ratio: 0.0,
        image_coverage_ratio: 0.05,
        vector_line_count: 42,
        deferred_regions_count: 0,
        table_presence: 'CONFIRMED_PRESENT',
      },
      {
        page_number: 2,
        page_type: 'SCANNED',
        processing_status: 'INCOMPLETE_DEFERRED_TO_OCR',
        printable_char_count: 0,
        garbled_char_ratio: 0.0,
        image_coverage_ratio: 0.98,
        vector_line_count: 0,
        deferred_regions_count: 1,
        table_presence: 'UNKNOWN_PENDING_OCR',
      },
    ];

    const { container } = render(<PageProfiles profiles={profiles} />);
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for StitchAudit cards', async () => {
    const events: StitchAuditEvent[] = [
      {
        upper_page: 1,
        lower_page: 2,
        upper_table_id: 'tbl-1',
        lower_table_id: 'tbl-2',
        decision: 'STITCH_CONFIRMED',
        header_similarity_score: 0.95,
        col_overlap_ratio: 0.92,
        type_compatibility_ratio: 0.9,
        repeated_header_rows_stripped: 1,
        reasons: ['High column overlap and identical column data types'],
      },
    ];

    const { container } = render(<StitchAudit stitchEvents={events} />);
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for Header component', async () => {
    const { container } = render(
      <Header
        isBackendConnected={true}
        onCheckBackend={vi.fn()}
        onOpenModelRegistry={vi.fn()}
      />
    );
    await expectNoA11yViolations(container);
  });

  it('passes WCAG audit for ModelRegistryDrawer when open', async () => {
    const { baseElement } = render(
      <ModelRegistryDrawer isOpen={true} onClose={vi.fn()} />
    );
    await expectNoA11yViolations(baseElement);
  });
});
