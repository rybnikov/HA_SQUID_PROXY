import type { HTMLAttributes } from 'react';

interface HAIconProps extends HTMLAttributes<HTMLElement> {
  icon: string;
  'data-testid'?: string;
}

const ICON_FALLBACK: Record<string, string> = {
  'mdi:arrow-left': '\u2190',
  'mdi:arrow-right': '\u2192',
  'mdi:close': '\u2715',
  'mdi:cog': '\u2699',
  'mdi:plus': '+',
  'mdi:delete': '\uD83D\uDDD1',
  'mdi:play': '\u25B6',
  'mdi:stop': '\u25A0',
  'mdi:server-network': '\uD83D\uDDA5',
  'mdi:check': '\u2713',
  'mdi:content-copy': '\u2398',
  'mdi:eye': '\uD83D\uDC41',
  'mdi:eye-off': '\u25CE',
  'mdi:refresh': '\u21BB',
  'mdi:magnify': '\uD83D\uDD0D',
  'mdi:download': '\u2B07',
  'mdi:alert': '\u26A0',
  'mdi:information': '\u2139',
  'mdi:shield-lock': '\uD83D\uDD12',
};

export function HAIcon({ icon, className, 'data-testid': testId, ...props }: HAIconProps) {
  const hasHaIcon = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-icon'));

  if (hasHaIcon) {
    return <ha-icon icon={icon} className={className} data-testid={testId} {...props} />;
  }

  const fallbackChar = ICON_FALLBACK[icon] ?? icon.replace('mdi:', '').charAt(0).toUpperCase();

  return (
    <span
      className={className}
      data-testid={testId}
      data-icon={icon}
      aria-label={icon}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '24px',
        height: '24px',
        fontSize: '18px',
        lineHeight: 1,
        ...(typeof props.style === 'object' ? props.style : {}),
      }}
      {...props}
      // Re-apply style after spread so our defaults merge correctly
    >
      {fallbackChar}
    </span>
  );
}
