import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../common';
import './layout.css';

export interface BackendStatusBannerProps {
  isVisible: boolean;
  onRetry: () => void;
  isRetrying?: boolean;
}

export const BackendStatusBanner: React.FC<BackendStatusBannerProps> = ({
  isVisible,
  onRetry,
  isRetrying = false,
}) => {
  if (!isVisible) return null;

  return (
    <div className="ds-backend-banner" role="alert">
      <div className="ds-backend-banner-inner">
        <div className="ds-backend-banner-message">
          <AlertCircle size={16} aria-hidden="true" />
          <span>
            <strong>Backend Unreachable:</strong> The FastAPI adapter at <code>http://127.0.0.1:8000</code> is not responding. Start the backend with <code>uvicorn app.api.app:app --port 8000</code> to enable document processing.
          </span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          isLoading={isRetrying}
          icon={<RefreshCw size={13} aria-hidden="true" />}
        >
          Retry Connection
        </Button>
      </div>
    </div>
  );
};
