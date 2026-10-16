import React from 'react';
import './common.css';

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  label,
  className = '',
  ...props
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`ds-spinner-wrapper ${className}`.trim()}
      {...props}
    >
      <span className={`ds-spinner ds-spinner-${size}`} aria-hidden="true" />
      {label ? (
        <span className="ds-spinner-label">{label}</span>
      ) : (
        <span
          className="sr-only"
          style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}
        >
          Loading...
        </span>
      )}
    </div>
  );
};
