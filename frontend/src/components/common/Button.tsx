import React, { forwardRef } from 'react';
import './common.css';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'secondary',
      size = 'md',
      isLoading = false,
      fullWidth = false,
      icon,
      iconPosition = 'left',
      disabled,
      className = '',
      ...props
    },
    ref
  ) => {
    const classNames = [
      'ds-btn',
      `ds-btn-${variant}`,
      `ds-btn-${size}`,
      fullWidth ? 'ds-btn-full' : '',
      isLoading ? 'ds-btn-loading' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={classNames}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading && (
          <span className="ds-spinner ds-spinner-sm" aria-hidden="true" />
        )}
        {!isLoading && icon && iconPosition === 'left' && (
          <span className="ds-btn-icon" aria-hidden="true">{icon}</span>
        )}
        <span>{children}</span>
        {!isLoading && icon && iconPosition === 'right' && (
          <span className="ds-btn-icon" aria-hidden="true">{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
