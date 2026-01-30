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
    <label className="flex flex-col gap-2 text-sm text-muted-foreground">
      <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</span>
      <select
        id={selectId}
        name={selectName}
        className={cn(
          'rounded-[12px] border border-muted bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none',
          className
        )}
        {...props}
      >
        {children}
      </select>
      {helperText && <span className="text-xs text-muted-foreground">{helperText}</span>}
    </label>
  );
}
