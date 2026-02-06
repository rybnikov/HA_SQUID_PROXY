import { useEffect, useRef } from 'react';
import type { ButtonHTMLAttributes, CSSProperties, HTMLAttributes, ReactNode } from 'react';

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

const hasHaButton = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-button'));

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
    if (!hasHaButton) return;
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

  if (hasHaButton) {
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
        {loading ? 'Loading\u2026 ' : null}
        {children}
      </ha-button>
    );
  }

  // Fallback: styled native button
  const isRaised = raised ?? (variant === 'primary' || variant === 'success');
  const isOutlined = outlined ?? (variant === 'secondary' || variant === 'danger');
  const isDisabled = disabled || loading;

  const fallbackStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: size === 'sm' ? '4px 12px' : size === 'lg' ? '10px 24px' : '6px 16px',
    fontSize: '14px',
    fontWeight: 500,
    fontFamily: 'inherit',
    borderRadius: '4px',
    cursor: isDisabled ? 'default' : 'pointer',
    opacity: isDisabled ? 0.38 : 1,
    transition: 'background 0.15s, border-color 0.15s, opacity 0.15s',
    letterSpacing: '0.02em',
    textTransform: 'uppercase' as const,
    whiteSpace: 'nowrap',
    lineHeight: '36px',
    minHeight: '36px',
    boxSizing: 'border-box',
  };

  if (isRaised) {
    const bg =
      variant === 'success' ? 'var(--success-color, #43a047)'
      : variant === 'danger' ? 'var(--error-color, #db4437)'
      : 'var(--primary-color, #009ac7)';
    Object.assign(fallbackStyle, {
      backgroundColor: bg,
      color: '#fff',
      border: 'none',
    });
  } else if (isOutlined) {
    const borderColor =
      variant === 'danger' ? 'var(--error-color, #db4437)'
      : variant === 'success' ? 'var(--success-color, #43a047)'
      : 'var(--primary-color, #009ac7)';
    const textColor =
      variant === 'danger' ? 'var(--error-color, #db4437)'
      : variant === 'success' ? 'var(--success-color, #43a047)'
      : 'var(--primary-color, #009ac7)';
    Object.assign(fallbackStyle, {
      backgroundColor: 'transparent',
      color: textColor,
      border: `1px solid ${borderColor}`,
    });
  } else {
    // Ghost / text button
    const textColor =
      variant === 'danger' ? 'var(--error-color, #db4437)'
      : variant === 'success' ? 'var(--success-color, #43a047)'
      : 'var(--primary-color, #009ac7)';
    Object.assign(fallbackStyle, {
      backgroundColor: 'transparent',
      color: textColor,
      border: 'none',
    });
  }

  const handleClick = () => {
    if (isDisabled) return;
    onClick?.();
  };

  return (
    <button
      type={type}
      className={className}
      disabled={isDisabled}
      onClick={handleClick}
      data-size={size}
      style={fallbackStyle}
      {...(props as ButtonHTMLAttributes<HTMLButtonElement>)}
    >
      {loading ? 'Loading\u2026 ' : null}
      {children}
    </button>
  );
}
