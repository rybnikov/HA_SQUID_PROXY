import { useEffect, useRef } from 'react';
import type { ButtonHTMLAttributes, HTMLAttributes } from 'react';

interface HAIconButtonProps extends Omit<HTMLAttributes<HTMLElement>, 'onClick'> {
  icon: string;
  label?: string;
  disabled?: boolean;
  onClick?: () => void;
}

export function HAIconButton({ icon, label, disabled, onClick, ...props }: HAIconButtonProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !onClick) return;

    const handler = () => {
      if (!disabled) onClick();
    };

    el.addEventListener('click', handler);
    return () => el.removeEventListener('click', handler);
  }, [disabled, onClick]);

  const hasNative =
    typeof customElements !== 'undefined' && Boolean(customElements.get('ha-icon-button'));

  if (hasNative) {
    return (
      <ha-icon-button
        ref={ref}
        disabled={disabled}
        aria-label={label}
        {...props}
      >
        <ha-icon icon={icon} />
      </ha-icon-button>
    );
  }

  const ICON_FALLBACK: Record<string, string> = {
    'mdi:arrow-left': '\u2190',
    'mdi:arrow-right': '\u2192',
    'mdi:close': '\u2715',
    'mdi:cog': '\u2699',
    'mdi:plus': '+',
    'mdi:delete': '\u{1F5D1}',
    'mdi:play': '\u25B6',
    'mdi:stop': '\u25A0',
    'mdi:server-network': '\u{1F5A5}',
    'mdi:check': '\u2713',
  };

  const fallbackText = ICON_FALLBACK[icon] ?? icon.replace('mdi:', '');

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      style={{
        background: 'none',
        border: 'none',
        cursor: disabled ? 'default' : 'pointer',
        padding: '8px',
        borderRadius: '50%',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--primary-text-color, inherit)',
        opacity: disabled ? 0.38 : 1,
        fontSize: '20px',
        width: '40px',
        height: '40px',
      }}
      {...(props as ButtonHTMLAttributes<HTMLButtonElement>)}
    >
      <span data-icon={icon} aria-hidden="true">
        {fallbackText}
      </span>
    </button>
  );
}
