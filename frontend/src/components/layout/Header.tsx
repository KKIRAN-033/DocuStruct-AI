import React from 'react';
import { Cpu, RefreshCw } from 'lucide-react';
import { Button } from '../common';
import incuxLogo from '../../assets/incux-logo.jpeg';
import './layout.css';

export interface HeaderProps {
  isBackendConnected: boolean | null;
  onCheckBackend: () => void;
  onOpenModelRegistry: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendConnected,
  onCheckBackend,
  onOpenModelRegistry,
}) => {
  const statusClass =
    isBackendConnected === true
      ? 'ds-status-connected'
      : isBackendConnected === false
      ? 'ds-status-disconnected'
      : 'ds-status-checking';

  const statusText =
    isBackendConnected === true
      ? 'Backend Connected'
      : isBackendConnected === false
      ? 'Backend Offline'
      : 'Checking Status...';

  return (
    <header className="ds-header" role="banner">
      <div className="ds-header-inner">
        <div className="ds-brand">
          <div className="ds-logo-mark">
            <img src={incuxLogo} alt="INCUXAI Logo" className="ds-logo-img" />
          </div>
          <div className="ds-brand-text">
            <div className="ds-brand-title-row">
              <span className="ds-brand-name">INCUXAI</span>
              <span className="ds-version-badge">v2.0.0</span>
            </div>
            <span className="ds-brand-tagline">
              Autonomous Document & Tabular AI Workstation
            </span>
          </div>
        </div>

        <div className="ds-header-actions">
          {/* Backend Connectivity Status Indicator */}
          <div
            className={`ds-status-indicator ${statusClass}`}
            role="status"
            aria-live="polite"
            title={
              isBackendConnected === true
                ? 'FastAPI adapter running on port 8000'
                : 'FastAPI adapter unreachable on port 8000'
            }
          >
            <span className="ds-status-indicator-dot" aria-hidden="true" />
            <span>{statusText}</span>
            {isBackendConnected === false && (
              <button
                type="button"
                onClick={onCheckBackend}
                aria-label="Retry backend connection"
                style={{ display: 'inline-flex', alignItems: 'center', marginLeft: 4 }}
              >
                <RefreshCw size={12} aria-hidden="true" />
              </button>
            )}
          </div>

          {/* Multi-LLM Model Registry Status Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenModelRegistry}
            icon={<Cpu size={14} aria-hidden="true" />}
            title="Inspect 7 registered AI candidates and provider status"
          >
            AI Models (Standby)
          </Button>
        </div>
      </div>
    </header>
  );
};
