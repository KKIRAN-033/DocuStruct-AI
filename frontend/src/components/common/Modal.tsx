import React from 'react';
import { X } from 'lucide-react';
import { useFocusTrap } from './useFocusTrap';
import './common.css';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: string;
  closeOnBackdropClick?: boolean;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = '32rem',
  closeOnBackdropClick = true,
}) => {
  const containerRef = useFocusTrap<HTMLDivElement>({
    isOpen,
    onClose,
    closeOnEscape: true,
  });

  if (!isOpen) return null;

  return (
    <div
      className="ds-modal-backdrop"
      role="presentation"
      onClick={closeOnBackdropClick ? onClose : undefined}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : 'Dialog'}
        tabIndex={-1}
        className="ds-modal-container"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ds-modal-header">
          {title && <h3 className="ds-modal-title">{title}</h3>}
          <button
            type="button"
            className="ds-btn ds-btn-ghost ds-btn-sm"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        <div className="ds-modal-body">{children}</div>
        {footer && <div className="ds-modal-footer">{footer}</div>}
      </div>
    </div>
  );
};
