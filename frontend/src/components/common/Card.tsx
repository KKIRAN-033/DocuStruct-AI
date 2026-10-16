import React from 'react';
import './common.css';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  actions,
  children,
  footer,
  className = '',
  ...props
}) => {
  const hasHeader = Boolean(title || subtitle || actions);

  return (
    <div className={`ds-card ${className}`.trim()} {...props}>
      {hasHeader && (
        <div className="ds-card-header">
          <div className="ds-card-title-group">
            {title && <h3 className="ds-card-title">{title}</h3>}
            {subtitle && <p className="ds-card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="ds-card-actions">{actions}</div>}
        </div>
      )}
      <div className="ds-card-body">{children}</div>
      {footer && <div className="ds-card-footer">{footer}</div>}
    </div>
  );
};
