import type { ReactNode } from 'react';

import { cn } from '@/utils/cn';

interface CardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, subtitle, action, children, className }: CardProps) {
  return (
    <div className={cn('rounded-card border border-border-subtle bg-card-bg shadow-card p-4 sm:p-6', className)}>
      {(title || action) && (
        <div className="mb-3 sm:mb-4 flex flex-col sm:flex-row items-start justify-between gap-3 sm:gap-4">
          <div className="min-w-0 flex-1">
            {title && <h3 className="text-base sm:text-lg font-semibold text-text-primary">{title}</h3>}
            {subtitle && <p className="text-sm text-text-secondary">{subtitle}</p>}
          </div>
          {action && <div className="w-full sm:w-auto flex-shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
