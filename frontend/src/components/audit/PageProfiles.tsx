import React from 'react';
import { Layers, AlertCircle } from 'lucide-react';
import { Badge } from '../common';
import type { PageProfile, PageType } from '../../types/domain';
import './audit.css';

export interface PageProfilesProps {
  profiles: PageProfile[];
}

export const PageProfiles: React.FC<PageProfilesProps> = ({ profiles }) => {
  if (!profiles || profiles.length === 0) {
    return (
      <div style={{ padding: 'var(--space-4)', color: 'var(--color-slate)', fontSize: 'var(--font-size-sm)' }}>
        No page profiles available.
      </div>
    );
  }

  const getPageTypeVariant = (type: PageType): 'verified' | 'warning' | 'failed' | 'deferred' | 'neutral' => {
    switch (type) {
      case 'DIGITAL':
        return 'verified';
      case 'SCANNED':
        return 'deferred';
      case 'HYBRID':
        return 'warning';
      case 'EMPTY_OR_UNREADABLE':
      default:
        return 'neutral';
    }
  };

  return (
    <div className="ds-audit-section" data-testid="page-profiles-section">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <Layers size={16} style={{ color: 'var(--color-cobalt)' }} aria-hidden="true" />
        <h3 style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
          Page-by-Page Diagnostic Profiles ({profiles.length} Pages)
        </h3>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="ds-audit-table" aria-label="Page Diagnostic Profiles">
          <thead>
            <tr>
              <th scope="col">Page</th>
              <th scope="col">Classification</th>
              <th scope="col">Processing Status</th>
              <th scope="col" style={{ textAlign: 'right' }}>Printable Chars</th>
              <th scope="col" style={{ textAlign: 'right' }}>Vector Lines</th>
              <th scope="col" style={{ textAlign: 'right' }}>Image Coverage</th>
              <th scope="col" style={{ textAlign: 'right' }}>Deferred OCR</th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((p) => {
              const isOcrDeferred =
                p.deferred_regions_count > 0 || p.processing_status === 'INCOMPLETE_DEFERRED_TO_OCR';

              return (
                <tr key={p.page_number} data-testid={`page-profile-row-${p.page_number}`}>
                  <td style={{ fontWeight: 600 }}>Page {p.page_number}</td>
                  <td>
                    <Badge variant={getPageTypeVariant(p.page_type)} size="sm">
                      {p.page_type}
                    </Badge>
                  </td>
                  <td>
                    <Badge
                      variant={
                        p.processing_status === 'EXTRACTED'
                          ? 'neutral'
                          : p.processing_status === 'INCOMPLETE_DEFERRED_TO_OCR'
                          ? 'deferred'
                          : 'warning'
                      }
                      size="sm"
                    >
                      {p.processing_status}
                    </Badge>
                  </td>
                  <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {p.printable_char_count}
                  </td>
                  <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {p.vector_line_count}
                  </td>
                  <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {(p.image_coverage_ratio * 100).toFixed(1)}%
                  </td>
                  <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {isOcrDeferred ? (
                      <span
                        style={{
                          color: 'var(--color-deferred-text)',
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        <AlertCircle size={12} aria-hidden="true" /> {p.deferred_regions_count} regions
                      </span>
                    ) : (
                      '0'
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
