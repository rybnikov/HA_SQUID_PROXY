import { cva, type VariantProps } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/utils/cn';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-[12px] font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-app-bg disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-white shadow-[0_12px_24px_rgba(0,188,212,0.2)] hover:bg-primary/90 focus-visible:ring-primary',
        secondary:
          'border border-border-default bg-transparent text-text-primary hover:border-text-secondary/70 hover:bg-white/5 focus-visible:ring-border-default',
        ghost: 'bg-transparent text-text-secondary hover:bg-white/5 hover:text-text-primary',
        danger: 'border border-danger text-danger hover:bg-danger/10 focus-visible:ring-danger',
        success:
          'bg-success text-white shadow-[0_12px_24px_rgba(76,175,80,0.2)] hover:bg-success/90 focus-visible:ring-success'
      },
      size: {
        sm: 'h-9 px-4 text-sm',
        md: 'h-10 px-5 text-sm',
        lg: 'h-12 px-6 text-base'
      }
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md'
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export function Button({ className, variant, size, loading, disabled, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : null}
      {children}
    </button>
  );
}
