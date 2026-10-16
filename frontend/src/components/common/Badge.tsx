import React from 'react';
import './common.css';

export type BadgeVariant =
  | 'verified'
  | 'warning'
  | 'failed'
  | 'discrepancy'
  | 'deferred'
  | 'neutral';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  withDot?: boolean;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  withDot = true,
  icon,
  className = '',
  ...props
}) => {
  const normalizedVariant = variant === 'discrepancy' ? 'failed' : variant;
  const classNames = [
    'ds-badge',
    `ds-badge-${normalizedVariant}`,
    size === 'sm' ? 'ds-badge-sm' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classNames} {...props}>
      {withDot && !icon && <span className="ds-badge-dot" aria-hidden="true" />}
      {icon && <span className="ds-badge-icon" aria-hidden="true">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
