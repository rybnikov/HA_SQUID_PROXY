import type { ReactNode } from 'react';

import { cn } from '@/utils/cn';

interface ModalProps {
  id: string;
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export function Modal({ id, title, isOpen, onClose, children, footer, className }: ModalProps) {
  const titleId = `${id}-title`;
  return (
    <div
      id={id}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-4 py-10 backdrop-blur-sm',
        !isOpen && 'hidden'
      )}
      aria-hidden={!isOpen}
    >
      <div
        className={cn(
          'w-full max-w-2xl rounded-[20px] border border-border-default bg-modal-bg shadow-[0_30px_70px_rgba(0,0,0,0.65)]',
          className
        )}
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-4 sm:px-8 py-4 sm:py-6">
          <h2 id={titleId} className="text-xl sm:text-2xl font-semibold text-text-primary">
            {title}
          </h2>
          <button
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border-subtle text-text-secondary transition-colors hover:bg-white/5 hover:text-text-primary hover:border-border-default flex-shrink-0"
            onClick={onClose}
            type="button"
            aria-label="Close"
            data-testid="modal-close-button"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-6 px-4 sm:px-8 py-4 sm:py-6 max-h-[calc(100vh-12rem)] overflow-y-auto">{children}</div>
        {footer && <div className="border-t border-border-subtle px-4 sm:px-8 py-4 sm:py-5">{footer}</div>}
      </div>
    </div>
  );
}
