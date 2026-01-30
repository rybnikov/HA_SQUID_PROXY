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
      <span className="text-xs uppercase tracking-[0.2em] text-text-secondary">{label}</span>
      <input
        ref={ref}
        id={inputId}
        name={inputName}
        className={cn(
          'rounded-[12px] border border-border-subtle bg-input-bg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none',
          className
        )}
        {...props}
      />
      {helperText && <span className="text-xs text-text-secondary">{helperText}</span>}
    </label>
  );
});
