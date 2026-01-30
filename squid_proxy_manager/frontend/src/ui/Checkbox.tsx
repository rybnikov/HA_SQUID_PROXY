import type { InputHTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Checkbox({ label, className, ...props }: CheckboxProps) {
  const checkboxId = props.id ?? props.name;
  const checkboxName = props.name ?? props.id;
  return (
    <label className="flex items-center gap-2 text-sm text-text-secondary">
      <input
        id={checkboxId}
        name={checkboxName}
        type="checkbox"
        className={cn(
          'h-4 w-4 rounded border-border-default bg-input-bg text-primary focus:ring-2 focus:ring-primary/40',
          className
        )}
        {...props}
      />
      <span className="text-text-primary">{label}</span>
    </label>
  );
}
