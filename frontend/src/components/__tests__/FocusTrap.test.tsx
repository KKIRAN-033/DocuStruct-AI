import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Modal, Drawer } from '../common';

describe('Accessible Dialog Keyboard Focus Trapping', () => {
  it('traps Tab navigation within Modal container', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Test Modal">
        <div>
          <button type="button" data-testid="first-btn">First Button</button>
          <input type="text" data-testid="text-input" placeholder="Type here" />
          <button type="button" data-testid="last-btn">Last Button</button>
        </div>
      </Modal>
    );

    const closeBtn = screen.getByLabelText('Close dialog');
    const firstBtn = screen.getByTestId('first-btn');
    const lastBtn = screen.getByTestId('last-btn');

    // Focus starts on close button
    expect(document.activeElement).toBe(closeBtn);

    // Tabbing from close button moves to first button
    fireEvent.keyDown(document, { key: 'Tab' });
    firstBtn.focus();
    expect(document.activeElement).toBe(firstBtn);

    // Tabbing from last focusable element wraps back to close button
    lastBtn.focus();
    expect(document.activeElement).toBe(lastBtn);

    fireEvent.keyDown(document, { key: 'Tab' });
    expect(document.activeElement).toBe(closeBtn);

    // Shift+Tab from close button wraps to last button
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(lastBtn);
  });

  it('traps Tab navigation within Drawer container', () => {
    const handleClose = vi.fn();
    render(
      <Drawer isOpen={true} onClose={handleClose} title="Test Drawer">
        <div>
          <button type="button" data-testid="drawer-btn-1">Button 1</button>
          <button type="button" data-testid="drawer-btn-2">Button 2</button>
        </div>
      </Drawer>
    );

    const closeBtn = screen.getByLabelText('Close drawer');
    const btn2 = screen.getByTestId('drawer-btn-2');

    expect(document.activeElement).toBe(closeBtn);

    btn2.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(document.activeElement).toBe(closeBtn);
  });

  it('dismisses Modal on Escape key press', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Escape Modal">
        <p>Modal Content</p>
      </Modal>
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('dismisses Drawer on Escape key press', () => {
    const handleClose = vi.fn();
    render(
      <Drawer isOpen={true} onClose={handleClose} title="Escape Drawer">
        <p>Drawer Content</p>
      </Drawer>
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
