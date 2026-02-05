import type { HTMLAttributes } from 'react';

interface HAIconProps extends HTMLAttributes<HTMLElement> {
  icon: string;
  'data-testid'?: string;
}

export function HAIcon({ icon, className, 'data-testid': testId, ...props }: HAIconProps) {
  const hasHaIcon = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-icon'));

  if (hasHaIcon) {
    return <ha-icon icon={icon} className={className} data-testid={testId} {...props} />;
  }

  // Fallback: display icon name as text placeholder
  return (
    <span
      className={className}
      data-testid={testId}
      data-icon={icon}
      aria-label={icon}
      {...props}
    >
      {icon.replace('mdi:', '')}
    </span>
  );
}
