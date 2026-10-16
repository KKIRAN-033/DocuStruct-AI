import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, ShieldCheck } from 'lucide-react';
import './common.css';

export type CalloutVariant = 'info' | 'warning' | 'danger' | 'success' | 'disclaimer';

export interface CalloutProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  variant?: CalloutVariant;
  title?: React.ReactNode;
  icon?: React.ReactNode;
}

const defaultIcons: Record<CalloutVariant, React.ReactNode> = {
  info: <Info size={18} aria-hidden="true" />,
  warning: <AlertTriangle size={18} aria-hidden="true" />,
  danger: <AlertCircle size={18} aria-hidden="true" />,
  success: <CheckCircle2 size={18} aria-hidden="true" />,
  disclaimer: <ShieldCheck size={18} aria-hidden="true" />,
};

export const Callout: React.FC<CalloutProps> = ({
  variant = 'info',
  title,
  icon,
  children,
  className = '',
  ...props
}) => {
  const displayIcon = icon ?? defaultIcons[variant];

  return (
    <div
      role="region"
      aria-label={typeof title === 'string' ? title : `${variant} notice`}
      className={`ds-callout ds-callout-${variant} ${className}`.trim()}
      {...props}
    >
      <div className="ds-callout-icon">{displayIcon}</div>
      <div className="ds-callout-content">
        {title && <div className="ds-callout-title">{title}</div>}
        <div className="ds-callout-message">{children}</div>
      </div>
    </div>
  );
};
