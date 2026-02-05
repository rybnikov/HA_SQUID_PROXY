import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

interface HADialogProps {
  id: string;
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}

/**
 * Dialog wrapper that uses a pure HTML/CSS overlay instead of native ha-dialog.
 * Native ha-dialog uses slot names (primaryAction/secondaryAction) that are
 * incompatible with React's single footer prop, and React can't reliably
 * set properties on Lit-based web components. The overlay approach works
 * consistently across all HA environments.
 */
export function HADialog({ id, title, isOpen, onClose, children, footer, className }: HADialogProps) {
  const backdropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      id={id}
      ref={backdropRef}
      className={className}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={(e) => {
        if (e.target === backdropRef.current) onClose();
      }}
    >
      <div style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
      }} />
      <div style={{
        position: 'relative',
        backgroundColor: 'var(--card-background-color, #1c1c1c)',
        color: 'var(--primary-text-color, #e1e1e1)',
        borderRadius: '12px',
        minWidth: '320px',
        maxWidth: '500px',
        width: '90vw',
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      }}>
        <h2 style={{
          margin: 0,
          padding: '16px 24px',
          fontSize: '1.25rem',
          fontWeight: 500,
        }}>
          {title}
        </h2>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
        {footer && (
          <div style={{
            padding: '8px 16px 16px',
            display: 'flex',
            justifyContent: 'flex-end',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
