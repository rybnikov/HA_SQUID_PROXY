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
  headerClassName?: string;
  titleClassName?: string;
  closeButtonClassName?: string;
  closeIconClassName?: string;
  bodyClassName?: string;
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export function Modal({
  id,
  title,
  isOpen,
  onClose,
  children,
  footer,
  className,
  headerClassName,
  titleClassName,
  closeButtonClassName,
  closeIconClassName,
  bodyClassName
}: ModalProps) {
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
        <div
          className={cn(
            'flex items-center justify-between border-b border-border-subtle px-4 sm:px-8 py-4 sm:py-6',
            headerClassName
          )}
        >
          <h2 id={titleId} className={cn('text-xl sm:text-2xl font-semibold text-text-primary', titleClassName)}>
            {title}
          </h2>
          <button
            className={cn(
              'flex h-8 w-8 items-center justify-center text-text-secondary transition-colors hover:text-text-primary flex-shrink-0',
              closeButtonClassName
            )}
            onClick={onClose}
            type="button"
            aria-label="Close"
            data-testid="modal-close-button"
          >
            <CloseIcon className={cn('h-6 w-6', closeIconClassName)} />
          </button>
        </div>
        <div
          className={cn(
            'space-y-6 px-4 sm:px-8 py-4 sm:py-6 max-h-[calc(100vh-12rem)] overflow-y-auto',
            bodyClassName
          )}
        >
          {children}
        </div>
        {footer && <div className="border-t border-border-subtle px-4 sm:px-8 py-4 sm:py-5">{footer}</div>}
      </div>
    </div>
  );
}
