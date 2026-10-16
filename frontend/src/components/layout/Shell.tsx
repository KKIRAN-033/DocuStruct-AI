import React from 'react';
import { Header } from './Header';
import { BackendStatusBanner } from './BackendStatusBanner';
import './layout.css';

export interface ShellProps {
  isBackendConnected: boolean | null;
  onCheckBackend: () => void;
  onOpenModelRegistry: () => void;
  isRetryingConnection?: boolean;
  children: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = ({
  isBackendConnected,
  onCheckBackend,
  onOpenModelRegistry,
  isRetryingConnection = false,
  children,
}) => {
  return (
    <div className="ds-shell">
      <Header
        isBackendConnected={isBackendConnected}
        onCheckBackend={onCheckBackend}
        onOpenModelRegistry={onOpenModelRegistry}
      />

      <BackendStatusBanner
        isVisible={isBackendConnected === false}
        onRetry={onCheckBackend}
        isRetrying={isRetryingConnection}
      />

      <main className="ds-main" id="main-content">
        {children}
      </main>

      <footer className="ds-footer" role="contentinfo">
        <div className="ds-footer-inner">
          <span>
            INCUXAI — Autonomous Document & Tabular AI Workstation
          </span>
          <span>
            Backend: {isBackendConnected ? 'Active (Port 8000)' : 'Offline'}
          </span>
        </div>
      </footer>
    </div>
  );
};
