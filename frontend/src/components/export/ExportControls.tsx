import React, { useState } from 'react';
import { Download, FileSpreadsheet, FileCode, Check, Archive } from 'lucide-react';
import { Button } from '../common';
import { apiClient } from '../../api/client';
import type { CanonicalTable, DocumentEvaluationReport } from '../../types/domain';

export interface ExportControlsProps {
  table: CanonicalTable;
  tables?: CanonicalTable[];
  activeTableIdx?: number;
  report?: DocumentEvaluationReport | null;
}

export const ExportControls: React.FC<ExportControlsProps> = ({
  table,
  tables,
  activeTableIdx,
  report,
}) => {
  const [isExportingCsv, setIsExportingCsv] = useState(false);
  const [isExportingJson, setIsExportingJson] = useState(false);
  const [isExportingZip, setIsExportingZip] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  /**
   * RFC 4180 CSV cell escape helper.
   */
  const escapeCsvCell = (val: string): string => {
    if (val === null || val === undefined) return '""';
    const stringVal = String(val);
    if (
      stringVal.includes(',') ||
      stringVal.includes('"') ||
      stringVal.includes('\n') ||
      stringVal.includes('\r')
    ) {
      return `"${stringVal.replace(/"/g, '""')}"`;
    }
    return `"${stringVal}"`;
  };

  /**
   * Client-Side RFC 4180 CSV Export with UTF-8 BOM for Microsoft Excel for a target table.
   */
  const handleExportTableCsv = async (targetTable: CanonicalTable, tableIdx?: number) => {
    setIsExportingCsv(true);
    setExportMessage(null);
    try {
      const headers =
        targetTable.normalized_headers && targetTable.normalized_headers.length > 0
          ? targetTable.normalized_headers
          : targetTable.original_headers;

      const headerRow = headers.map(escapeCsvCell).join(',');
      const dataRows = targetTable.rows
        .filter((row) => {
          if (row.length === headers.length) {
            const matches = row.filter((cell, i) => {
              const val = (cell.accepted_value || cell.raw_value || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
              const hdr = (headers[i] || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
              return val && hdr && (val === hdr || val.includes(hdr) || hdr.includes(val));
            }).length;
            if (matches >= headers.length - 1) return false;
          }
          return true;
        })
        .map((row) =>
          row.map((cell) => escapeCsvCell(cell.accepted_value)).join(',')
        );

      // Prepend UTF-8 BOM (\ufeff) so Microsoft Excel opens it directly without encoding prompts
      const csvContent = '\ufeff' + [headerRow, ...dataRows].join('\r\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

      const titlePart = targetTable.title ? `_${targetTable.title.replace(/[^a-zA-Z0-9_-]/g, '_')}` : '';
      const prefix = tableIdx !== undefined ? `Table_${tableIdx + 1}` : (targetTable.table_id || 'table').replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${prefix}${titlePart}.csv`;

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExportMessage(`Table ${tableIdx !== undefined ? tableIdx + 1 : ''} CSV exported successfully.`);
    } catch {
      // Fallback: server-side export
      try {
        const blob = await apiClient.exportCsv(targetTable);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${targetTable.table_id || 'table'}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (err) {
        setExportMessage('Failed to export CSV.');
      }
    } finally {
      setIsExportingCsv(false);
    }
  };

  /**
   * Export All Distinct Tables as a ZIP Archive containing separate Excel CSV files.
   */
  const handleExportAllZip = async () => {
    if (!tables || tables.length === 0) return;
    setIsExportingZip(true);
    setExportMessage(null);
    try {
      // 1. Try server-side zip endpoint
      const blob = await apiClient.exportZip(tables);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `INCUXAI_All_${tables.length}_Tables.zip`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExportMessage(`All ${tables.length} tables exported to ZIP archive.`);
    } catch {
      // 2. Fallback: trigger sequential individual CSV downloads client-side
      try {
        tables.forEach((t, i) => {
          setTimeout(() => {
            const headers =
              t.normalized_headers && t.normalized_headers.length > 0
                ? t.normalized_headers
                : t.original_headers;
            const headerRow = headers.map(escapeCsvCell).join(',');
            const dataRows = t.rows
              .filter((row) => {
                if (row.length === headers.length) {
                  const matches = row.filter((cell, cIdx) => {
                    const val = (cell.accepted_value || cell.raw_value || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
                    const hdr = (headers[cIdx] || '').replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
                    return val && hdr && (val === hdr || val.includes(hdr) || hdr.includes(val));
                  }).length;
                  if (matches >= headers.length - 1) return false;
                }
                return true;
              })
              .map((row) =>
                row.map((cell) => escapeCsvCell(cell.accepted_value)).join(',')
              );

            const csvContent = '\ufeff' + [headerRow, ...dataRows].join('\r\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const title = t.title ? `_${t.title.replace(/[^a-zA-Z0-9_-]/g, '_')}` : '';
            const safeName = `Table_${i + 1}${title}.csv`;
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', safeName);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
          }, i * 300);
        });
        setExportMessage(`Downloading ${tables.length} tables as individual Excel CSV files...`);
      } catch {
        setExportMessage('Failed to export all tables.');
      }
    } finally {
      setIsExportingZip(false);
    }
  };

  /**
   * Lossless Structured Table JSON Export.
   */
  const handleExportJson = async () => {
    setIsExportingJson(true);
    setExportMessage(null);
    try {
      const headers =
        table.normalized_headers && table.normalized_headers.length > 0
          ? table.normalized_headers
          : table.original_headers;

      const rowsData = table.rows.map((row) =>
        row.map((cell) => cell.accepted_value)
      );

      const payload = {
        table_id: table.table_id,
        headers,
        rows: rowsData,
        source_pages: table.source_pages,
        structural_checks_passed: table.structural_checks_passed,
        math_validation_outcome: table.math_validation_outcome,
      };

      const jsonStr = JSON.stringify(payload, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });

      const safeId = (table.table_id || 'table').replace(/[^a-zA-Z0-9_-]/g, '_');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${safeId}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExportMessage('Table JSON exported successfully.');
    } catch {
      // Fallback: server-side export
      try {
        const blob = await apiClient.exportJson(table);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${table.table_id || 'table'}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (err) {
        setExportMessage('Failed to export JSON.');
      }
    } finally {
      setIsExportingJson(false);
    }
  };

  /**
   * Complete Document Report Export.
   */
  const handleExportReport = () => {
    if (!report) return;
    const jsonStr = JSON.stringify(report, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `incuxai_report_${report.job_id || 'job'}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const hasMultipleTables = Boolean(tables && tables.length > 1);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        flexWrap: 'wrap',
      }}
      data-testid="export-controls"
    >
      {/* 1. Independent Table Export Buttons */}
      {hasMultipleTables && tables ? (
        tables.map((t, idx) => {
          const isCurrent = idx === (activeTableIdx ?? 0);
          return (
            <Button
              key={t.table_id || idx}
              variant={isCurrent ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => handleExportTableCsv(t, idx)}
              disabled={isExportingCsv}
              aria-label={`Export table as CSV or Excel spreadsheet (Table ${idx + 1})`}
              data-testid={`export-table-${idx + 1}-btn`}
              title={`Download Table ${idx + 1}: ${t.title || `Table ${idx + 1}`} (${t.rows.length} rows) as Excel CSV`}
            >
              <FileSpreadsheet size={14} style={{ marginRight: 6 }} aria-hidden="true" />
              {isExportingCsv && isCurrent ? 'Exporting...' : `Export Table ${idx + 1}`}
            </Button>
          );
        })
      ) : (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleExportTableCsv(table)}
          disabled={isExportingCsv}
          aria-label="Export table as CSV or Excel spreadsheet"
          data-testid="export-csv-btn"
          title="Download table as CSV spreadsheet (opens directly in Microsoft Excel)"
        >
          <FileSpreadsheet size={14} style={{ marginRight: 6 }} aria-hidden="true" />
          {isExportingCsv ? 'Exporting...' : 'Export Excel / CSV'}
        </Button>
      )}

      {/* 2. All Tables ZIP Archive Export */}
      {hasMultipleTables && tables && (
        <Button
          variant="secondary"
          size="sm"
          onClick={handleExportAllZip}
          disabled={isExportingZip}
          aria-label="Export all distinct tables as ZIP archive"
          data-testid="export-all-zip-btn"
          title={`Download all ${tables.length} distinct tables as separate Excel spreadsheets inside a ZIP archive`}
        >
          <Archive size={14} style={{ marginRight: 6 }} aria-hidden="true" />
          {isExportingZip ? 'Zipping...' : `Export All Tables (${tables.length} Files / ZIP)`}
        </Button>
      )}

      {/* 3. JSON and Report Exports */}
      <Button
        variant="secondary"
        size="sm"
        onClick={handleExportJson}
        disabled={isExportingJson}
        aria-label="Export table as JSON"
      >
        <FileCode size={14} style={{ marginRight: 6 }} aria-hidden="true" />
        {isExportingJson ? 'Exporting...' : 'Export Table JSON'}
      </Button>

      {report && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleExportReport}
          aria-label="Export full audit report as JSON"
        >
          <Download size={14} style={{ marginRight: 6 }} aria-hidden="true" />
          Full Report JSON
        </Button>
      )}

      {exportMessage && (
        <span
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-verified-text)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <Check size={12} aria-hidden="true" /> {exportMessage}
        </span>
      )}
    </div>
  );
};

