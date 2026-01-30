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
  return (
    <label className="flex flex-col gap-2 text-sm text-muted-foreground">
      <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</span>
      <input
        ref={ref}
        className={cn(
          'rounded-[12px] border border-muted bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none',
          className
        )}
        {...props}
      />
      {helperText && <span className="text-xs text-muted-foreground">{helperText}</span>}
    </label>
  );
});
