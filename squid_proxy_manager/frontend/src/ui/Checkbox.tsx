import type { InputHTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Checkbox({ label, className, ...props }: CheckboxProps) {
  const checkboxId = props.id ?? props.name;
  const checkboxName = props.name ?? props.id;
  return (
    <label className="flex items-center justify-between gap-4 text-sm text-text-secondary cursor-pointer group">
      <span className="text-text-primary group-hover:text-text-primary transition-colors">{label}</span>
      <span className="relative inline-flex items-center">
        <input
          id={checkboxId}
          name={checkboxName}
          type="checkbox"
          className={cn('peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0', className)}
          {...props}
        />
        <span className="pointer-events-none h-6 w-12 rounded-full bg-[#3b3b3b] transition-colors peer-checked:bg-primary peer-hover:bg-[#4a4a4a] peer-focus-visible:ring-2 peer-focus-visible:ring-primary/50" />
        <span className="pointer-events-none absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-all peer-checked:translate-x-6" />
      </span>
    </label>
  );
}
