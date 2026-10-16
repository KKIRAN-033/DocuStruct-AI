import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button, Badge, Card, Callout, Modal, Spinner } from '../common';
import { MANDATORY_VERBATIM_DISCLAIMER } from '../../types/domain';

describe('Common Components', () => {
  describe('Button', () => {
    it('renders text and handles clicks', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click Me</Button>);

      const btn = screen.getByRole('button', { name: /click me/i });
      expect(btn).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders disabled state and blocks clicks', () => {
      const handleClick = vi.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);

      const btn = screen.getByRole('button', { name: /disabled/i });
      expect(btn).toBeDisabled();
      fireEvent.click(btn);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('displays loading state and disables interaction', () => {
      render(<Button isLoading>Process</Button>);
      const btn = screen.getByRole('button');
      expect(btn).toBeDisabled();
      expect(btn).toHaveAttribute('aria-busy', 'true');
    });

    it('applies variant and size classes', () => {
      const { container } = render(<Button variant="primary" size="lg">Primary Large</Button>);
      const btn = container.querySelector('button');
      expect(btn).toHaveClass('ds-btn-primary');
      expect(btn).toHaveClass('ds-btn-lg');
    });
  });

  describe('Badge', () => {
    it('renders semantic variants with dots', () => {
      const { container } = render(<Badge variant="verified">Verified</Badge>);
      expect(screen.getByText('Verified')).toBeInTheDocument();
      expect(container.querySelector('.ds-badge-dot')).toBeInTheDocument();
      expect(container.firstChild).toHaveClass('ds-badge-verified');
    });
  });

  describe('Card', () => {
    it('renders title, subtitle, and body content', () => {
      render(
        <Card title="Test Title" subtitle="Test Subtitle" footer={<div>Footer</div>}>
          <p>Body Content</p>
        </Card>
      );
      expect(screen.getByText('Test Title')).toBeInTheDocument();
      expect(screen.getByText('Test Subtitle')).toBeInTheDocument();
      expect(screen.getByText('Body Content')).toBeInTheDocument();
      expect(screen.getByText('Footer')).toBeInTheDocument();
    });
  });

  describe('Callout', () => {
    it('renders disclaimer variant with verbatim text', () => {
      render(
        <Callout variant="disclaimer" title="Disclaimer">
          {MANDATORY_VERBATIM_DISCLAIMER}
        </Callout>
      );
      expect(screen.getByText('Disclaimer')).toBeInTheDocument();
      expect(screen.getByText(MANDATORY_VERBATIM_DISCLAIMER)).toBeInTheDocument();
    });
  });

  describe('Spinner', () => {
    it('renders accessible label and spinner element', () => {
      render(<Spinner label="Loading documents..." />);
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Loading documents...')).toBeInTheDocument();
    });
  });

  describe('Modal', () => {
    it('renders when open and handles escape key', () => {
      const handleClose = vi.fn();
      const { rerender } = render(
        <Modal isOpen={false} onClose={handleClose} title="Modal Title">
          Modal Content
        </Modal>
      );

      expect(screen.queryByText('Modal Title')).not.toBeInTheDocument();

      rerender(
        <Modal isOpen={true} onClose={handleClose} title="Modal Title">
          Modal Content
        </Modal>
      );

      expect(screen.getByText('Modal Title')).toBeInTheDocument();
      expect(screen.getByText('Modal Content')).toBeInTheDocument();

      fireEvent.keyDown(document, { key: 'Escape' });
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });
});
