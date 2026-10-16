import React, { useState, useRef, useCallback } from 'react';
import { UploadCloud, FileText, X, RefreshCw } from 'lucide-react';
import { Button, Spinner, Callout } from '../common';
import { apiClient, MAX_FILE_SIZE_BYTES } from '../../api/client';
import type { ApiError } from '../../types/api';
import type { DocumentEvaluationReport } from '../../types/domain';
import './upload.css';

export interface DocumentUploadProps {
  onExtractionSuccess: (report: DocumentEvaluationReport) => void;
  onExtractionError?: (error: ApiError) => void;
  isBackendConnected?: boolean | null;
}

export type UploadState = 'IDLE' | 'FILE_SELECTED' | 'PROCESSING' | 'ERROR';

const formatFileSize = (bytes: number): string => {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
};

const validateFile = (file: File): string | null => {
  // 1. Extension and MIME check
  const isPdfExt = file.name.toLowerCase().endsWith('.pdf');
  const isImageExt = /\.(png|jpe?g|webp|tiff|bmp)$/i.test(file.name);
  const isPdfMime = file.type === 'application/pdf' || file.type === '';
  const isImageMime = file.type.startsWith('image/');
  if (!isPdfExt && !isPdfMime && !isImageExt && !isImageMime) {
    return 'Only PDF documents (.pdf) are supported for deterministic table extraction.';
  }

  // 2. Pre-flight size check (50 MiB ceiling)
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File exceeds the 50 MiB operational limit (selected: ${formatFileSize(file.size)}).`;
  }

  if (file.size === 0) {
    return 'The selected file is empty (0 bytes). Please provide a valid PDF.';
  }

  return null;
};

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onExtractionSuccess,
  onExtractionError,
  isBackendConnected = true,
}) => {
  const [uploadState, setUploadState] = useState<UploadState>('IDLE');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [processingPhase, setProcessingPhase] = useState<string>(
    'Initiating deterministic extraction...'
  );

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleFileSelection = useCallback((file: File) => {
    setErrorMessage(null);
    const error = validateFile(file);
    if (error) {
      setErrorMessage(error);
      setUploadState('ERROR');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    setUploadState('FILE_SELECTED');
  }, []);

  const onDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        handleFileSelection(file);
      }
    },
    [handleFileSelection]
  );

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleRunExtraction = async () => {
    if (!selectedFile) return;

    setUploadState('PROCESSING');
    setErrorMessage(null);
    setProcessingPhase('Uploading document and routing pages...');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // Phase 1: Uploading & Routing
      const report = await apiClient.extractDocument(selectedFile, controller.signal);
      setUploadState('IDLE');
      setSelectedFile(null);
      onExtractionSuccess(report);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr.detail || 'Extraction failed. Please verify document integrity and retry.');
      setUploadState('ERROR');
      onExtractionError?.(apiErr);
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleCancelExtraction = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setUploadState('FILE_SELECTED');
    setErrorMessage('Extraction cancelled by user.');
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    setUploadState('IDLE');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="ds-upload-container">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf,image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
        style={{ display: 'none' }}
        onChange={onFileInputChange}
        data-testid="file-input"
        aria-label="Upload PDF or Document Image"
      />

      {/* IDLE State: Dropzone */}
      {uploadState === 'IDLE' && (
        <div
          role="button"
          tabIndex={0}
          className={`ds-dropzone ${isDragging ? 'ds-dropzone-active' : ''} ${
            isBackendConnected === false ? 'ds-dropzone-disabled' : ''
          }`}
          onDragEnter={onDragEnter}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={openFileDialog}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              openFileDialog();
            }
          }}
          aria-label="Drag and drop PDF document here, or click to browse"
        >
          <div className="ds-dropzone-icon" aria-hidden="true">
            <UploadCloud size={28} />
          </div>
          <h3 className="ds-dropzone-title">Upload PDF for Deterministic Extraction & Document Images</h3>
          <p className="ds-dropzone-desc">
            Drag and drop your financial PDF, scanned invoice, receipt photo, or table image here, or click to browse.
          </p>
          <div className="ds-dropzone-meta">
            <span>Format: PDF & Document Images (Vision AI)</span>
            <span>•</span>
            <span>Max Size: 50 MiB</span>
            <span>•</span>
            <span>Up to 100 pages</span>
          </div>
        </div>
      )}

      {/* FILE_SELECTED State: File card & Action button */}
      {uploadState === 'FILE_SELECTED' && selectedFile && (
        <div className="ds-selected-file-card">
          <div className="ds-file-info">
            <div className="ds-file-icon" aria-hidden="true">
              <FileText size={22} />
            </div>
            <div className="ds-file-details">
              <span className="ds-file-name" title={selectedFile.name}>
                {selectedFile.name}
              </span>
              <span className="ds-file-size">{formatFileSize(selectedFile.size)}</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunExtraction}
              disabled={isBackendConnected === false}
            >
              Run Extraction
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              aria-label="Remove selected file"
            >
              <X size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}

      {/* PROCESSING State: Indeterminate loader with honest textual phase indicator */}
      {uploadState === 'PROCESSING' && (
        <div className="ds-upload-processing-box" role="status" aria-live="polite">
          <Spinner size="lg" label="Processing document" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span className="ds-processing-phase">{processingPhase}</span>
            <span className="ds-processing-subtext">
              Executing ruling-line geometry analysis, exact Decimal arithmetic verification, and quality gate inspection.
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={handleCancelExtraction}>
            Cancel Extraction
          </Button>
        </div>
      )}

      {/* ERROR State: Error callout with retry or reset */}
      {uploadState === 'ERROR' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <Callout variant="danger" title="Extraction Barrier Encountered">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <span>{errorMessage}</span>
              <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                <Button variant="secondary" size="sm" onClick={handleRemoveFile}>
                  <RefreshCw size={14} style={{ marginRight: 6 }} aria-hidden="true" /> Select Another Document
                </Button>
              </div>
            </div>
          </Callout>
        </div>
      )}
    </div>
  );
};
