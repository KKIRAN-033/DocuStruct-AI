import React from 'react';
import { MANDATORY_VERBATIM_DISCLAIMER } from '../../types/domain';
import './status.css';

export interface VerbatimDisclaimerProps {
  className?: string;
}

export const VerbatimDisclaimer: React.FC<VerbatimDisclaimerProps> = ({ className = '' }) => {
  return (
    <div
      className={`ds-verbatim-disclaimer-box ${className}`}
      role="note"
      aria-label="Statutory Limitation Disclaimer"
      data-testid="verbatim-disclaimer"
    >
      <span className="ds-disclaimer-title">Mandatory Audit Limitation Disclaimer</span>
      <p className="ds-disclaimer-text">
        &ldquo;{MANDATORY_VERBATIM_DISCLAIMER}&rdquo;
      </p>
    </div>
  );
};
