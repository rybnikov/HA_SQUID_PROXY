import type { SelectHTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  helperText?: string;
}

export function Select({ label, helperText, className, children, ...props }: SelectProps) {
  const selectId = props.id ?? props.name;
  const selectName = props.name ?? props.id;
  return (
    <label className="flex flex-col gap-2 text-sm text-text-secondary">
      <span className="text-xs uppercase tracking-[0.2em] text-text-secondary">{label}</span>
      <select
        id={selectId}
        name={selectName}
        className={cn(
          'rounded-[12px] border border-border-subtle bg-input-bg px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none',
          className
        )}
        {...props}
      >
        {children}
      </select>
      {helperText && <span className="text-xs text-text-secondary">{helperText}</span>}
    </label>
  );
}
