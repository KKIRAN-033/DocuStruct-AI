import { useEffect, useRef } from 'react';

const FOCUSABLE_SELECTOR =
  'a[href], area[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
  ).filter((el) => {
    if (el.hasAttribute('disabled')) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;
    if (el.style.display === 'none' || el.style.visibility === 'hidden') return false;
    return true;
  });
}

interface UseFocusTrapOptions {
  isOpen: boolean;
  onClose?: () => void;
  closeOnEscape?: boolean;
}

export function useFocusTrap<T extends HTMLElement>(options: UseFocusTrapOptions) {
  const { isOpen, onClose, closeOnEscape = true } = options;
  const containerRef = useRef<T>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    previousActiveElementRef.current = document.activeElement as HTMLElement | null;

    const container = containerRef.current;
    if (!container) return;

    // Focus the first focusable element inside the container, or the container itself
    const focusables = getFocusableElements(container);

    if (focusables.length > 0) {
      focusables[0].focus();
    } else {
      container.focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (closeOnEscape && e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose?.();
        return;
      }

      if (e.key === 'Tab') {
        const currentFocusables = getFocusableElements(container);

        if (currentFocusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = currentFocusables[0];
        const last = currentFocusables[currentFocusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || document.activeElement === container) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
      previousActiveElementRef.current?.focus?.();
    };
  }, [isOpen, onClose, closeOnEscape]);

  return containerRef;
}
