import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, helperText, className, ...props },
  ref
) {
  const inputId = props.id ?? props.name;
  const inputName = props.name ?? props.id;
  return (
    <label className="flex flex-col gap-2 text-sm text-text-secondary">
      <span className="text-xs uppercase tracking-[0.18em] text-text-secondary">{label}</span>
      <input
        ref={ref}
        id={inputId}
        name={inputName}
        className={cn(
          'rounded-[12px] border border-border-default bg-input-bg px-4 py-3 text-sm text-text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] placeholder:text-text-muted focus:border-primary focus:outline-none transition-colors',
          className
        )}
        {...props}
      />
      {helperText && <span className="text-xs text-text-secondary">{helperText}</span>}
    </label>
  );
});
