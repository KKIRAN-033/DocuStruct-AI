import React from 'react';
import { X } from 'lucide-react';
import { useFocusTrap } from './useFocusTrap';
import './common.css';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  width?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = '36rem',
}) => {
  const containerRef = useFocusTrap<HTMLDivElement>({
    isOpen,
    onClose,
    closeOnEscape: true,
  });

  if (!isOpen) return null;

  return (
    <div
      className="ds-drawer-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : 'Drawer'}
        tabIndex={-1}
        className="ds-drawer-container"
        style={{ maxWidth: width }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ds-drawer-header">
          {title && <h3 className="ds-modal-title">{title}</h3>}
          <button
            type="button"
            className="ds-btn ds-btn-ghost ds-btn-sm"
            onClick={onClose}
            aria-label="Close drawer"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="ds-drawer-body">{children}</div>
      </div>
    </div>
  );
};
