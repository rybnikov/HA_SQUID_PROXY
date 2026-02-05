import { useEffect, useRef } from 'react';
import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';

export interface HAButtonProps
  extends Omit<HTMLAttributes<HTMLElement>, 'onClick' | 'children'>,
    Partial<{ variant: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'; size: 'sm' | 'md' | 'lg' }> {
  children: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  raised?: boolean;
  outlined?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

export function HAButton({
  children,
  className,
  disabled,
  loading,
  onClick,
  raised,
  outlined,
  type = 'button',
  variant,
  size,
  ...props
}: HAButtonProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const clickHandler = () => {
      if (disabled || loading) return;
      onClick?.();

      const form = el.closest('form');
      if (!form) return;
      if (type === 'submit') {
        form.requestSubmit();
      } else if (type === 'reset') {
        form.reset();
      }
    };

    el.addEventListener('click', clickHandler);
    return () => el.removeEventListener('click', clickHandler);
  }, [disabled, loading, onClick, type]);

  const variantStyle: CSSProperties | undefined =
    variant === 'danger'
      ? {
          '--mdc-theme-primary': 'var(--error-color, #db4437)',
          color: 'var(--error-color, #db4437)',
        } as CSSProperties
      : variant === 'success'
        ? {
            '--mdc-theme-primary': 'var(--success-color, #43a047)',
            color: 'var(--success-color, #43a047)',
          } as CSSProperties
        : undefined;

  return (
    <ha-button
      ref={ref}
      className={className}
      disabled={disabled || loading}
      raised={raised ?? (variant === 'primary' || variant === 'success')}
      outlined={outlined ?? (variant === 'secondary' || variant === 'danger')}
      data-size={size}
      aria-disabled={disabled || loading}
      style={variantStyle}
      {...props}
    >
      {loading ? 'Loading… ' : null}
      {children}
    </ha-button>
  );
}
